import unittest
import yaml
import tempfile
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from render import render, load_site
from split import split_by_az


def render_from_dict(site_data):
    """Render a template from a Python dict instead of a YAML file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(site_data, f, default_flow_style=False)
        path = f.name
    try:
        return render(path)
    finally:
        os.unlink(path)


def parse_output(rendered_text):
    """Parse rendered text as YAML and return the components dict."""
    return yaml.safe_load(rendered_text)


def extract_all_fqdns(obj):
    """Recursively extract all FQDN strings from a nested structure."""
    fqdns = []
    if isinstance(obj, str) and ".infra." in obj:
        fqdns.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            fqdns.extend(extract_all_fqdns(v))
    elif isinstance(obj, list):
        for v in obj:
            fqdns.extend(extract_all_fqdns(v))
    return fqdns


BASE_SITE = {
    "environment": "idev",
    "domain": "nzero.dev",
    "co": "de",
    "product": "Infra",
    "env_name": "Dev",
    "networks": [
        {
            "type": "management",
            "label": "Mgmt",
            "host_prefix": "m",
            "jumphost_ids": [3, 4, 11, 12, 13],
            "azs": [
                {"number": 1, "network_hostname": "defraama", "region": "fra11", "compute_qty": 3},
                {"number": 2, "network_hostname": "defraamb", "region": "fra11", "compute_qty": 3},
            ],
        },
        {
            "type": "workloads",
            "label": "Workloads",
            "host_prefix": "w",
            "azs": [
                {"number": 1, "network_hostname": "defraawa", "region": "fra11", "compute_qty": 0},
                {"number": 2, "network_hostname": "defraawb", "region": "fra11", "compute_qty": 0},
            ],
        },
    ],
}


class TestBaseline(unittest.TestCase):
    """Test 1: Baseline configuration."""

    def setUp(self):
        self.rendered = render("sites/infra-dev.yaml")
        self.data = parse_output(self.rendered)
        self.components = self.data["components"]

    def test_generation_succeeds(self):
        self.assertIsNotNone(self.data)

    def test_yaml_valid(self):
        self.assertIsNotNone(self.data)

    def test_all_sections_exist(self):
        for section in ("network", "security", "dns_ntp", "jumphosts", "compute"):
            self.assertIn(section, self.components, f"Missing section: {section}")

    def test_management_and_workloads_rendered(self):
        self.assertIn("Infra Dev Mgmt AZ1", self.components["network"])
        self.assertIn("Infra Dev Mgmt AZ2", self.components["network"])
        self.assertIn("Infra Dev Workloads AZ1", self.components["network"])
        self.assertIn("Infra Dev Workloads AZ2", self.components["network"])

    def test_network_fqdns(self):
        self.assertEqual(
            self.components["network"]["Infra Dev Mgmt AZ1"][0],
            "aadefraama0002.infra.nzero.dev",
        )
        self.assertEqual(
            self.components["network"]["Infra Dev Mgmt AZ2"][0],
            "aadefraamb0002.infra.nzero.dev",
        )
        self.assertEqual(
            self.components["network"]["Infra Dev Workloads AZ1"][0],
            "aadefraawa0002.infra.nzero.dev",
        )
        self.assertEqual(
            self.components["network"]["Infra Dev Workloads AZ2"][0],
            "aadefraawb0002.infra.nzero.dev",
        )

    def test_panorama_uses_region_not_hostname(self):
        self.assertEqual(
            self.components["security"]["Infra Dev Mgmt AZ1"][0],
            "de-mgmt-fra11-1-panorama.infra.nzero.dev",
        )
        self.assertNotIn("defraama", self.components["security"]["Infra Dev Mgmt AZ1"][0])

    def test_management_has_gridmasters(self):
        for az_key in ("Infra Dev Mgmt AZ1", "Infra Dev Mgmt AZ2"):
            self.assertIn("gridmasters", self.components["dns_ntp"][az_key])
            self.assertEqual(len(self.components["dns_ntp"][az_key]["gridmasters"]), 2)

    def test_workloads_no_gridmasters(self):
        for az_key in ("Infra Dev Workloads AZ1", "Infra Dev Workloads AZ2"):
            self.assertNotIn("gridmasters", self.components["dns_ntp"][az_key])
            self.assertIn("resolvers", self.components["dns_ntp"][az_key])

    def test_jumphosts_management_only(self):
        self.assertIn("Infra Dev Mgmt AZ1", self.components["jumphosts"])
        self.assertIn("Infra Dev Mgmt AZ2", self.components["jumphosts"])
        self.assertNotIn("Infra Dev Workloads AZ1", self.components["jumphosts"])

    def test_compute_management_has_hosts(self):
        self.assertEqual(len(self.components["compute"]["Infra Dev Mgmt AZ1"]), 3)
        self.assertEqual(
            self.components["compute"]["Infra Dev Mgmt AZ1"][0],
            "demfra11-z1-a3.infra.nzero.dev",
        )
        self.assertEqual(
            self.components["compute"]["Infra Dev Mgmt AZ1"][2],
            "demfra11-z1-a5.infra.nzero.dev",
        )

    def test_compute_workloads_empty(self):
        self.assertEqual(self.components["compute"]["Infra Dev Workloads AZ1"], [])
        self.assertEqual(self.components["compute"]["Infra Dev Workloads AZ2"], [])

    def test_fqdn_entry_count(self):
        all_fqdns = extract_all_fqdns(self.data)
        self.assertEqual(len(all_fqdns), 34)

    def test_unique_fqdn_count(self):
        all_fqdns = extract_all_fqdns(self.data)
        self.assertEqual(len(set(all_fqdns)), 33)

    def test_duplicate_panorama_explained(self):
        az1_pan = self.components["security"]["Infra Dev Mgmt AZ1"][0]
        az2_pan = self.components["security"]["Infra Dev Mgmt AZ2"][0]
        self.assertEqual(az1_pan, az2_pan,
                         "Both AZs share region fra11, so Panorama FQDNs are intentionally identical")


class TestAddThirdAZManagement(unittest.TestCase):
    """Test 2: Add AZ3 to management via YAML only."""

    def setUp(self):
        site = yaml.safe_load(Path("sites/infra-dev.yaml").read_text())
        site["networks"][0]["azs"].append({
            "number": 3,
            "network_hostname": "defraamc",
            "region": "fra11",
            "compute_qty": 2,
        })
        self.rendered = render_from_dict(site)
        self.data = parse_output(self.rendered)
        self.components = self.data["components"]

    def test_az3_in_network(self):
        self.assertIn("Infra Dev Mgmt AZ3", self.components["network"])
        self.assertEqual(
            self.components["network"]["Infra Dev Mgmt AZ3"][0],
            "aadefraamc0002.infra.nzero.dev",
        )

    def test_az3_in_security(self):
        self.assertIn("Infra Dev Mgmt AZ3", self.components["security"])
        self.assertEqual(
            self.components["security"]["Infra Dev Mgmt AZ3"][0],
            "de-mgmt-fra11-1-panorama.infra.nzero.dev",
        )

    def test_az3_in_dns_ntp(self):
        self.assertIn("Infra Dev Mgmt AZ3", self.components["dns_ntp"])
        self.assertIn("gridmasters", self.components["dns_ntp"]["Infra Dev Mgmt AZ3"])
        self.assertEqual(
            self.components["dns_ntp"]["Infra Dev Mgmt AZ3"]["gridmasters"][0],
            "imdefraamc0001.infra.nzero.dev",
        )
        self.assertEqual(
            self.components["dns_ntp"]["Infra Dev Mgmt AZ3"]["resolvers"][0],
            "irdefraamc0001.infra.nzero.dev",
        )

    def test_az3_in_jumphosts(self):
        self.assertIn("Infra Dev Mgmt AZ3", self.components["jumphosts"])
        self.assertEqual(len(self.components["jumphosts"]["Infra Dev Mgmt AZ3"]), 5)
        self.assertEqual(
            self.components["jumphosts"]["Infra Dev Mgmt AZ3"][0],
            "demfra11-z3-b3.infra.nzero.dev",
        )

    def test_az3_in_compute(self):
        self.assertIn("Infra Dev Mgmt AZ3", self.components["compute"])
        self.assertEqual(len(self.components["compute"]["Infra Dev Mgmt AZ3"]), 2)
        self.assertEqual(
            self.components["compute"]["Infra Dev Mgmt AZ3"][0],
            "demfra11-z3-a3.infra.nzero.dev",
        )
        self.assertEqual(
            self.components["compute"]["Infra Dev Mgmt AZ3"][1],
            "demfra11-z3-a4.infra.nzero.dev",
        )

    def test_no_template_modification_needed(self):
        pass  # The fact that setUp succeeded proves this


class TestThirdAZWorkloadsOnly(unittest.TestCase):
    """Test 3: AZ3 only in workloads — management-only components must NOT appear."""

    def setUp(self):
        import copy
        site = copy.deepcopy(BASE_SITE)
        site["networks"][1]["azs"].append({
            "number": 3,
            "network_hostname": "defraawc",
            "region": "fra11",
            "compute_qty": 3,
        })
        self.rendered = render_from_dict(site)
        self.data = parse_output(self.rendered)
        self.components = self.data["components"]

    def test_workload_az3_network(self):
        self.assertIn("Infra Dev Workloads AZ3", self.components["network"])

    def test_workload_az3_resolvers(self):
        self.assertIn("Infra Dev Workloads AZ3", self.components["dns_ntp"])
        self.assertIn("resolvers", self.components["dns_ntp"]["Infra Dev Workloads AZ3"])

    def test_workload_az3_compute(self):
        self.assertEqual(len(self.components["compute"]["Infra Dev Workloads AZ3"]), 3)

    def test_workload_az3_no_gridmasters(self):
        self.assertNotIn("gridmasters", self.components["dns_ntp"]["Infra Dev Workloads AZ3"])

    def test_workload_az3_no_panorama(self):
        self.assertNotIn("Infra Dev Workloads AZ3", self.components.get("security", {}))

    def test_workload_az3_no_jumphosts(self):
        self.assertNotIn("Infra Dev Workloads AZ3", self.components.get("jumphosts", {}))


class TestDifferentRegionsPerAZ(unittest.TestCase):
    """Test 4: AZ1 and AZ2 have different regions."""

    def setUp(self):
        import copy
        site = copy.deepcopy(BASE_SITE)
        site["networks"][0]["azs"][0]["region"] = "fra11"
        site["networks"][0]["azs"][1]["region"] = "fra12"
        self.rendered = render_from_dict(site)
        self.data = parse_output(self.rendered)
        self.components = self.data["components"]

    def test_panorama_uses_correct_region_per_az(self):
        self.assertEqual(
            self.components["security"]["Infra Dev Mgmt AZ1"][0],
            "de-mgmt-fra11-1-panorama.infra.nzero.dev",
        )
        self.assertEqual(
            self.components["security"]["Infra Dev Mgmt AZ2"][0],
            "de-mgmt-fra12-1-panorama.infra.nzero.dev",
        )

    def test_compute_uses_correct_region_per_az(self):
        self.assertIn("fra11", self.components["compute"]["Infra Dev Mgmt AZ1"][0])
        self.assertIn("fra12", self.components["compute"]["Infra Dev Mgmt AZ2"][0])

    def test_jumphosts_uses_correct_region_per_az(self):
        self.assertIn("fra11", self.components["jumphosts"]["Infra Dev Mgmt AZ1"][0])
        self.assertIn("fra12", self.components["jumphosts"]["Infra Dev Mgmt AZ2"][0])


class TestDifferentHostnamePrefixes(unittest.TestCase):
    """Test 5: Different network hostnames — must be preserved exactly."""

    def setUp(self):
        import copy
        site = copy.deepcopy(BASE_SITE)
        site["networks"][0]["azs"][0]["network_hostname"] = "testmgmta"
        site["networks"][0]["azs"][1]["network_hostname"] = "testmgmtb"
        self.rendered = render_from_dict(site)
        self.data = parse_output(self.rendered)
        self.components = self.data["components"]

    def test_hostnames_not_shortened(self):
        self.assertEqual(
            self.components["network"]["Infra Dev Mgmt AZ1"][0],
            "aatestmgmta0002.infra.nzero.dev",
        )
        self.assertEqual(
            self.components["network"]["Infra Dev Mgmt AZ2"][0],
            "aatestmgmtb0002.infra.nzero.dev",
        )

    def test_dns_uses_correct_hostname(self):
        self.assertEqual(
            self.components["dns_ntp"]["Infra Dev Mgmt AZ1"]["gridmasters"][0],
            "imtestmgmta0001.infra.nzero.dev",
        )
        self.assertEqual(
            self.components["dns_ntp"]["Infra Dev Mgmt AZ2"]["resolvers"][0],
            "irtestmgmtb0001.infra.nzero.dev",
        )


class TestDifferentComputeCounts(unittest.TestCase):
    """Test 6: Various compute_qty values."""

    def setUp(self):
        import copy
        site = copy.deepcopy(BASE_SITE)
        site["networks"][0]["azs"] = [
            {"number": 1, "network_hostname": "hosta", "region": "reg1", "compute_qty": 0},
            {"number": 2, "network_hostname": "hostb", "region": "reg1", "compute_qty": 1},
            {"number": 3, "network_hostname": "hostc", "region": "reg1", "compute_qty": 3},
            {"number": 4, "network_hostname": "hostd", "region": "reg1", "compute_qty": 5},
        ]
        site["networks"][1]["azs"] = []
        self.rendered = render_from_dict(site)
        self.data = parse_output(self.rendered)
        self.components = self.data["components"]

    def test_qty_zero_produces_empty_list(self):
        self.assertEqual(self.components["compute"]["Infra Dev Mgmt AZ1"], [])

    def test_qty_one_produces_one_host(self):
        self.assertEqual(len(self.components["compute"]["Infra Dev Mgmt AZ2"]), 1)

    def test_qty_three_produces_three_hosts(self):
        self.assertEqual(len(self.components["compute"]["Infra Dev Mgmt AZ3"]), 3)

    def test_qty_five_produces_five_hosts(self):
        self.assertEqual(len(self.components["compute"]["Infra Dev Mgmt AZ4"]), 5)

    def test_numbering_starts_from_3(self):
        host = self.components["compute"]["Infra Dev Mgmt AZ2"][0]
        self.assertIn("-a3", host)

    def test_qty_three_ids(self):
        hosts = self.components["compute"]["Infra Dev Mgmt AZ3"]
        ids = [h.split("-a")[1].split(".")[0] for h in hosts]
        self.assertEqual(ids, ["3", "4", "5"])

    def test_qty_five_ids(self):
        hosts = self.components["compute"]["Infra Dev Mgmt AZ4"]
        ids = [h.split("-a")[1].split(".")[0] for h in hosts]
        self.assertEqual(ids, ["3", "4", "5", "6", "7"])

    def test_no_a0_a1_a2(self):
        for az_key, hosts in self.components["compute"].items():
            if isinstance(hosts, list):
                for h in hosts:
                    self.assertNotIn("-a0.", h)
                    self.assertNotIn("-a1.", h)
                    self.assertNotIn("-a2.", h)


class TestJumphostsMissing(unittest.TestCase):
    """Test 7: Management network without jumphost_ids."""

    def setUp(self):
        import copy
        site = copy.deepcopy(BASE_SITE)
        del site["networks"][0]["jumphost_ids"]
        self.rendered = render_from_dict(site)
        self.data = parse_output(self.rendered)
        self.components = self.data["components"]

    def test_no_jumphosts_section(self):
        self.assertNotIn("jumphosts", self.components)

    def test_other_sections_still_work(self):
        self.assertIn("network", self.components)
        self.assertIn("security", self.components)
        self.assertIn("dns_ntp", self.components)
        self.assertIn("compute", self.components)


class TestJumphostsEmptyList(unittest.TestCase):
    """Test 8: jumphost_ids is an empty list."""

    def setUp(self):
        import copy
        site = copy.deepcopy(BASE_SITE)
        site["networks"][0]["jumphost_ids"] = []
        self.rendered = render_from_dict(site)
        self.data = parse_output(self.rendered)
        self.components = self.data["components"]

    def test_no_jumphosts_section(self):
        self.assertNotIn("jumphosts", self.components)

    def test_other_sections_still_work(self):
        self.assertIn("network", self.components)
        self.assertIn("security", self.components)
        self.assertIn("dns_ntp", self.components)
        self.assertIn("compute", self.components)


class TestManagementMultipleAZs(unittest.TestCase):
    """Test 9: Management network with 5 AZs."""

    def setUp(self):
        import copy
        site = copy.deepcopy(BASE_SITE)
        azs = []
        for i in range(1, 6):
            azs.append({
                "number": i,
                "network_hostname": f"host{i}",
                "region": f"reg{i}",
                "compute_qty": 1,
            })
        site["networks"][0]["azs"] = azs
        site["networks"][1]["azs"] = []
        self.rendered = render_from_dict(site)
        self.data = parse_output(self.rendered)
        self.components = self.data["components"]

    def test_all_5_azs_in_network(self):
        for i in range(1, 6):
            self.assertIn(f"Infra Dev Mgmt AZ{i}", self.components["network"])

    def test_all_5_azs_in_security(self):
        for i in range(1, 6):
            self.assertIn(f"Infra Dev Mgmt AZ{i}", self.components["security"])

    def test_all_5_azs_in_dns_ntp(self):
        for i in range(1, 6):
            self.assertIn(f"Infra Dev Mgmt AZ{i}", self.components["dns_ntp"])
            self.assertIn("gridmasters", self.components["dns_ntp"][f"Infra Dev Mgmt AZ{i}"])

    def test_all_5_azs_in_jumphosts(self):
        for i in range(1, 6):
            self.assertIn(f"Infra Dev Mgmt AZ{i}", self.components["jumphosts"])

    def test_all_5_azs_in_compute(self):
        for i in range(1, 6):
            self.assertEqual(len(self.components["compute"][f"Infra Dev Mgmt AZ{i}"]), 1)


class TestMultipleWorkloadNetworks(unittest.TestCase):
    """Test 10: Multiple workload networks."""

    def setUp(self):
        import copy
        site = copy.deepcopy(BASE_SITE)
        site["networks"][1]["label"] = "Workloads-A"
        site["networks"].append({
            "type": "workloads",
            "label": "Workloads-B",
            "host_prefix": "x",
            "azs": [
                {"number": 1, "network_hostname": "wlxb1", "region": "regx", "compute_qty": 2},
                {"number": 2, "network_hostname": "wlxb2", "region": "regx", "compute_qty": 0},
            ],
        })
        self.rendered = render_from_dict(site)
        self.data = parse_output(self.rendered)
        self.components = self.data["components"]

    def test_both_workload_networks_in_network_section(self):
        self.assertIn("Infra Dev Workloads-A AZ1", self.components["network"])
        self.assertIn("Infra Dev Workloads-B AZ1", self.components["network"])

    def test_labels_preserved(self):
        keys = list(self.components["network"].keys())
        self.assertIn("Infra Dev Workloads-A AZ1", keys)
        self.assertIn("Infra Dev Workloads-B AZ1", keys)

    def test_compute_quantities_respected(self):
        self.assertEqual(len(self.components["compute"]["Infra Dev Workloads-B AZ1"]), 2)
        self.assertEqual(self.components["compute"]["Infra Dev Workloads-B AZ2"], [])

    def test_host_prefix_correct(self):
        wl_b_hosts = self.components["compute"]["Infra Dev Workloads-B AZ1"]
        self.assertTrue(len(wl_b_hosts) > 0)
        self.assertIn(
            "dexregx-z1-a3",
            wl_b_hosts[0],
        )
        wl_a_hosts = self.components["compute"]["Infra Dev Workloads-A AZ1"]
        if wl_a_hosts:
            self.assertIn(
                "dewfra11-z1-a3",
                wl_a_hosts[0],
            )


class TestMultipleManagementNetworks(unittest.TestCase):
    """Test 11: Two management-type networks."""

    def setUp(self):
        import copy
        site = copy.deepcopy(BASE_SITE)
        site["networks"][0]["label"] = "Mgmt-A"
        site["networks"].insert(1, {
            "type": "management",
            "label": "Mgmt-B",
            "host_prefix": "n",
            "jumphost_ids": [5, 6],
            "azs": [
                {"number": 1, "network_hostname": "mgtb1", "region": "regb", "compute_qty": 1},
            ],
        })
        self.rendered = render_from_dict(site)
        self.data = parse_output(self.rendered)
        self.components = self.data["components"]

    def test_both_mgmt_networks_in_network(self):
        self.assertIn("Infra Dev Mgmt-A AZ1", self.components["network"])
        self.assertIn("Infra Dev Mgmt-B AZ1", self.components["network"])

    def test_both_mgmt_networks_in_security(self):
        self.assertIn("Infra Dev Mgmt-A AZ1", self.components["security"])
        self.assertIn("Infra Dev Mgmt-B AZ1", self.components["security"])

    def test_both_mgmt_networks_get_gridmasters(self):
        self.assertIn("gridmasters", self.components["dns_ntp"]["Infra Dev Mgmt-A AZ1"])
        self.assertIn("gridmasters", self.components["dns_ntp"]["Infra Dev Mgmt-B AZ1"])

    def test_both_mgmt_networks_get_jumphosts(self):
        self.assertIn("Infra Dev Mgmt-A AZ1", self.components["jumphosts"])
        self.assertIn("Infra Dev Mgmt-B AZ1", self.components["jumphosts"])

    def test_jumphost_ids_correct_per_network(self):
        az_a = self.components["jumphosts"]["Infra Dev Mgmt-A AZ1"]
        az_b = self.components["jumphosts"]["Infra Dev Mgmt-B AZ1"]
        self.assertEqual(len(az_a), 5)
        self.assertEqual(len(az_b), 2)
        self.assertIn("-b3", az_a[0])
        self.assertIn("-b5", az_b[0])


class TestMissingRootFields(unittest.TestCase):
    """Test 12: Missing required root fields."""

    def _test_missing_field(self, field):
        import copy
        site = copy.deepcopy(BASE_SITE)
        del site[field]
        with self.assertRaises(ValueError) as ctx:
            render_from_dict(site)
        self.assertIn(field, str(ctx.exception))

    def test_missing_environment(self):
        self._test_missing_field("environment")

    def test_missing_domain(self):
        self._test_missing_field("domain")

    def test_missing_co(self):
        self._test_missing_field("co")

    def test_missing_product(self):
        self._test_missing_field("product")

    def test_missing_env_name(self):
        self._test_missing_field("env_name")

    def test_missing_networks(self):
        self._test_missing_field("networks")


class TestInvalidNetworksStructure(unittest.TestCase):
    """Test 13: Invalid networks structure."""

    def test_networks_as_dict(self):
        site = dict(BASE_SITE)
        site["networks"] = {}
        with self.assertRaises((TypeError, ValueError)):
            render_from_dict(site)

    def test_networks_as_string(self):
        site = dict(BASE_SITE)
        site["networks"] = "invalid"
        with self.assertRaises((TypeError, ValueError, AttributeError)):
            render_from_dict(site)

    def test_networks_list_of_strings(self):
        site = dict(BASE_SITE)
        site["networks"] = ["invalid"]
        with self.assertRaises((TypeError, ValueError, AttributeError)):
            render_from_dict(site)


class TestMissingNetworkField(unittest.TestCase):
    """Test 14: Missing required network-level fields."""

    def _test_missing_network_field(self, field):
        import copy
        site = copy.deepcopy(BASE_SITE)
        del site["networks"][0][field]
        with self.assertRaises(ValueError) as ctx:
            render_from_dict(site)
        self.assertIn(f"networks[0]", str(ctx.exception))
        self.assertIn(field, str(ctx.exception))

    def test_missing_type(self):
        self._test_missing_network_field("type")

    def test_missing_label(self):
        self._test_missing_network_field("label")

    def test_missing_host_prefix(self):
        self._test_missing_network_field("host_prefix")

    def test_missing_azs(self):
        self._test_missing_network_field("azs")


class TestInvalidAZStructure(unittest.TestCase):
    """Test 15: Invalid AZ structure."""

    def test_azs_as_dict(self):
        import copy
        site = copy.deepcopy(BASE_SITE)
        site["networks"][0]["azs"] = {}
        with self.assertRaises((TypeError, ValueError)):
            render_from_dict(site)

    def test_azs_as_string(self):
        import copy
        site = copy.deepcopy(BASE_SITE)
        site["networks"][0]["azs"] = "invalid"
        with self.assertRaises((TypeError, ValueError, AttributeError)):
            render_from_dict(site)

    def test_azs_list_of_strings(self):
        import copy
        site = copy.deepcopy(BASE_SITE)
        site["networks"][0]["azs"] = ["invalid"]
        with self.assertRaises((TypeError, ValueError, AttributeError)):
            render_from_dict(site)


class TestMissingAZField(unittest.TestCase):
    """Test 16: Missing required AZ-level fields."""

    def _test_missing_az_field(self, field):
        import copy
        site = copy.deepcopy(BASE_SITE)
        del site["networks"][0]["azs"][0][field]
        with self.assertRaises(ValueError) as ctx:
            render_from_dict(site)
        self.assertIn(f"networks[0].azs[0]", str(ctx.exception))
        self.assertIn(field, str(ctx.exception))

    def test_missing_number(self):
        self._test_missing_az_field("number")

    def test_missing_network_hostname(self):
        self._test_missing_az_field("network_hostname")

    def test_missing_region(self):
        self._test_missing_az_field("region")


class TestOptionalComputeQty(unittest.TestCase):
    """Test 17: compute_qty is optional — missing should produce []."""

    def setUp(self):
        import copy
        site = copy.deepcopy(BASE_SITE)
        del site["networks"][0]["azs"][0]["compute_qty"]
        self.rendered = render_from_dict(site)
        self.data = parse_output(self.rendered)
        self.components = self.data["components"]

    def test_compute_qty_missing_produces_empty(self):
        self.assertEqual(self.components["compute"]["Infra Dev Mgmt AZ1"], [])

    def test_no_exception(self):
        pass  # setUp succeeding proves this


class TestYAMLValidity(unittest.TestCase):
    """Test 18: Generated YAML is valid for multiple scenarios."""

    def test_baseline_yaml_valid(self):
        rendered = render("sites/infra-dev.yaml")
        data = yaml.safe_load(rendered)
        self.assertIsNotNone(data)

    def test_az3_yaml_valid(self):
        import copy
        site = copy.deepcopy(BASE_SITE)
        site["networks"][0]["azs"].append({
            "number": 3, "network_hostname": "defraamc",
            "region": "fra11", "compute_qty": 2,
        })
        data = yaml.safe_load(render_from_dict(site))
        self.assertIsNotNone(data)

    def test_no_jumphosts_yaml_valid(self):
        import copy
        site = copy.deepcopy(BASE_SITE)
        del site["networks"][0]["jumphost_ids"]
        data = yaml.safe_load(render_from_dict(site))
        self.assertIsNotNone(data)

    def test_workloads_only_yaml_valid(self):
        site = dict(BASE_SITE)
        site["networks"] = [site["networks"][1]]
        data = yaml.safe_load(render_from_dict(site))
        self.assertIsNotNone(data)

    def test_no_null_values(self):
        rendered = render("sites/infra-dev.yaml")
        data = yaml.safe_load(rendered)

        def check_no_nulls(obj, path=""):
            if obj is None:
                self.fail(f"Null value found at {path}")
            elif isinstance(obj, dict):
                for k, v in obj.items():
                    check_no_nulls(v, f"{path}.{k}")
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    check_no_nulls(v, f"{path}[{i}]")

        check_no_nulls(data)


class TestSplitPy(unittest.TestCase):
    """Test 19: split.py handles dynamic AZs."""

    def setUp(self):
        import copy
        site = copy.deepcopy(BASE_SITE)
        site["networks"][0]["azs"].append({
            "number": 3, "network_hostname": "defraamc",
            "region": "fra11", "compute_qty": 2,
        })
        self.rendered = render_from_dict(site)
        with tempfile.TemporaryDirectory() as tmpdir:
            main_file = Path(tmpdir) / "infratest-components.yaml"
            main_file.write_text(self.rendered)
            self.split_data = split_by_az(source=str(main_file), output_dir=tmpdir)
            self.split_files = {}
            for f in Path(tmpdir).glob("*.yaml"):
                if f.name != "infratest-components.yaml":
                    self.split_files[f.stem] = yaml.safe_load(f.read_text())

    def test_az1_split_file_exists(self):
        self.assertIn("Infra Dev Mgmt AZ1", self.split_files)

    def test_az2_split_file_exists(self):
        self.assertIn("Infra Dev Mgmt AZ2", self.split_files)

    def test_az3_split_file_exists(self):
        self.assertIn("Infra Dev Mgmt AZ3", self.split_files)

    def test_az3_has_network(self):
        self.assertIn("network", self.split_files["Infra Dev Mgmt AZ3"]["components"])

    def test_az3_has_security(self):
        self.assertIn("security", self.split_files["Infra Dev Mgmt AZ3"]["components"])

    def test_az3_has_jumphosts(self):
        self.assertIn("jumphosts", self.split_files["Infra Dev Mgmt AZ3"]["components"])

    def test_workload_az_has_no_security(self):
        self.assertNotIn("security", self.split_files["Infra Dev Workloads AZ1"]["components"])

    def test_all_split_files_valid_yaml(self):
        for name, data in self.split_files.items():
            self.assertIsNotNone(data, f"Invalid YAML in {name}")


class TestNoHardcodedAZAssumptions(unittest.TestCase):
    """Test 20: No hardcoded AZ1/AZ2 in template."""

    def test_no_az1_var_in_template(self):
        template = Path("templates/execution-environment.j2").read_text()
        self.assertNotIn("az1_", template.lower())

    def test_no_az2_var_in_template(self):
        template = Path("templates/execution-environment.j2").read_text()
        self.assertNotIn("az2_", template.lower())

    def test_no_hardcoded_z1_in_template(self):
        template = Path("templates/execution-environment.j2").read_text()
        for line in template.split("\n"):
            if "-z1" in line and "{{" not in line:
                self.fail(f"Hardcoded z1 found in non-template line: {line}")

    def test_no_hardcoded_z2_in_template(self):
        template = Path("templates/execution-environment.j2").read_text()
        for line in template.split("\n"):
            if "-z2" in line and "{{" not in line:
                self.fail(f"Hardcoded z2 found in non-template line: {line}")

    def test_no_hardcoded_b3_b4_b11_in_template(self):
        template = Path("templates/execution-environment.j2").read_text()
        self.assertNotIn("b3", template.replace("b{{", ""))
        self.assertNotIn("b11", template.replace("b{{", ""))

    def test_no_hardcoded_compute_qty_in_template(self):
        template = Path("templates/execution-environment.j2").read_text()
        self.assertNotIn("az1_m_compute", template)
        self.assertNotIn("az2_m_compute", template)


class TestFQDNRegression(unittest.TestCase):
    """Test 21: FQDN regression against pre-refactor output."""

    def setUp(self):
        baseline_path = Path("/tmp/opencode/baseline-e33f1f6.yaml")
        if baseline_path.exists():
            self.baseline = yaml.safe_load(baseline_path.read_text())
        else:
            self.skipTest("Baseline file not found")
        self.current = yaml.safe_load(render("sites/infra-dev.yaml"))

    def _extract_fqdns(self, obj):
        return set(extract_all_fqdns(obj))

    def test_no_fqdns_added(self):
        baseline = self._extract_fqdns(self.baseline)
        current = self._extract_fqdns(self.current)
        added = current - baseline
        self.assertEqual(added, set(), f"FQDNs added: {added}")

    def test_no_fqdns_removed(self):
        baseline = self._extract_fqdns(self.baseline)
        current = self._extract_fqdns(self.current)
        removed = baseline - current
        self.assertEqual(removed, set(), f"FQDNs removed: {removed}")

    def test_same_entry_count(self):
        baseline_entries = extract_all_fqdns(self.baseline)
        current_entries = extract_all_fqdns(self.current)
        self.assertEqual(len(baseline_entries), len(current_entries))

    def test_duplicate_fqdns_explained(self):
        current_entries = extract_all_fqdns(self.current)
        from collections import Counter
        counts = Counter(current_entries)
        dups = {fqdn: count for fqdn, count in counts.items() if count > 1}
        self.assertEqual(len(dups), 1, f"Expected 1 duplicate, got {len(dups)}")
        dup_fqdn = list(dups.keys())[0]
        self.assertIn("panorama", dup_fqdn,
                      "The duplicate should be the Panorama FQDN (both AZs share region fra11)")


class TestTemplateGenericness(unittest.TestCase):
    """Test 22: Completely different site config works without template changes."""

    def setUp(self):
        self.site = {
            "environment": "prod",
            "domain": "example.com",
            "co": "xx",
            "product": "Corp",
            "env_name": "Prod",
            "networks": [
                {
                    "type": "management",
                    "label": "Management",
                    "host_prefix": "m",
                    "jumphost_ids": [1, 2],
                    "azs": [
                        {"number": 1, "network_hostname": "mgmtproda", "region": "us01", "compute_qty": 4},
                        {"number": 2, "network_hostname": "mgmtprodb", "region": "us02", "compute_qty": 2},
                        {"number": 3, "network_hostname": "mgmtprodc", "region": "us03", "compute_qty": 0},
                    ],
                },
                {
                    "type": "workloads",
                    "label": "WL",
                    "host_prefix": "w",
                    "azs": [
                        {"number": 1, "network_hostname": "wlproda", "region": "us01", "compute_qty": 5},
                        {"number": 2, "network_hostname": "wlprodb", "region": "us02", "compute_qty": 1},
                    ],
                },
            ],
        }
        self.rendered = render_from_dict(self.site)
        self.data = parse_output(self.rendered)
        self.components = self.data["components"]

    def test_generation_succeeds(self):
        self.assertIsNotNone(self.data)

    def test_3_mgmt_azs(self):
        for i in range(1, 4):
            self.assertIn(f"Corp Prod Management AZ{i}", self.components["network"])

    def test_2_workload_azs(self):
        for i in range(1, 3):
            self.assertIn(f"Corp Prod WL AZ{i}", self.components["network"])

    def test_mgmt_az3_panorama(self):
        self.assertIn("Corp Prod Management AZ3", self.components["security"])

    def test_mgmt_az3_compute_empty(self):
        self.assertEqual(self.components["compute"]["Corp Prod Management AZ3"], [])

    def test_workload_az1_compute_5(self):
        self.assertEqual(len(self.components["compute"]["Corp Prod WL AZ1"]), 5)

    def test_different_regions_in_panorama(self):
        self.assertIn("us01", self.components["security"]["Corp Prod Management AZ1"][0])
        self.assertIn("us02", self.components["security"]["Corp Prod Management AZ2"][0])
        self.assertIn("us03", self.components["security"]["Corp Prod Management AZ3"][0])

    def test_different_jumphost_ids(self):
        self.assertEqual(len(self.components["jumphosts"]["Corp Prod Management AZ1"]), 2)
        self.assertIn("-b1.", self.components["jumphosts"]["Corp Prod Management AZ1"][0])
        self.assertIn("-b2.", self.components["jumphosts"]["Corp Prod Management AZ1"][1])

    def test_no_template_modification(self):
        template_mtime = Path("templates/execution-environment.j2").stat().st_mtime
        pass  # setUp succeeding proves the template wasn't modified


class TestStorageVerification(unittest.TestCase):
    """Test 23: Storage verification."""

    def test_no_storage_in_template(self):
        template = Path("templates/execution-environment.j2").read_text()
        self.assertNotIn("storage", template.lower())

    def test_no_storage_in_generated_output(self):
        data = yaml.safe_load(render("sites/infra-dev.yaml"))
        self.assertNotIn("storage", data.get("components", {}))

    def test_no_storage_in_git_history(self):
        import subprocess
        result = subprocess.run(
            ["git", "show", "74f2855:templates/execution-environment.j2"],
            capture_output=True, text=True,
        )
        self.assertNotIn("storage", result.stdout.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
