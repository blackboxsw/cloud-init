"""Home of the tests for end-to-end net rendering

Tests defined here should take a v1 or v2 yaml config as input, and verify
that the rendered network config is as expected. Input files are defined
under `tests/unittests/net/artifacts` with the format of

<test_name><format>.yaml

For example, if my test name is "test_all_the_things" and I'm testing a
v2 format, I should have a file named test_all_the_things_v2.yaml.

If a renderer outputs multiple files, the expected files should live in
the artifacts directory under the given test name. For example, if I'm
expecting NetworkManager to output a file named eth0.nmconnection as
part of my "test_all_the_things" test, then in the artifacts directory
there should be a
`test_all_the_things/etc/NetworkManager/system-connections/eth0.nmconnection`
file.

To add a new nominal test, create the input and output files, then add the test
name to the `test_convert` test along with it's supported renderers.

Before adding a test here, check that it is not already represented
in `unittests/test_net.py`. While that file contains similar tests, it has
become too large to be maintainable.
"""
import glob
import os
from enum import Flag, auto
from pathlib import Path

import pytest

from cloudinit import safeyaml
from cloudinit.net.netplan import Renderer as NetplanRenderer
from cloudinit.net.network_manager import Renderer as NetworkManagerRenderer
from cloudinit.net.network_state import NetworkState, parse_net_config_data

ARTIFACT_DIR = Path(__file__).parent.absolute() / "artifacts"


class Renderer(Flag):
    Netplan = auto()
    NetworkManager = auto()
    Networkd = auto()


@pytest.fixture(autouse=True)
def setup(mocker):
    mocker.patch("cloudinit.net.network_state.get_interfaces_by_mac")


def _dir_to_path_dict(dirname, test_name):
    result = {}
    for (dir_path, _, file_names) in os.walk(dirname):
        subdir = Path(dir_path.replace(f"{dirname}/{test_name}/", ""))
        for file_name in file_names:
            file_path = Path(dir_path, file_name)
            result[str(subdir / file_name)] = file_path.read_text()
    return result


def _assert_expected_config_file_artifacts(
    expected_dir, result_dir, test_name
):
    result_files = _dir_to_path_dict(result_dir, test_name)
    expected_files = _dir_to_path_dict(expected_dir, test_name)
    assert sorted(result_files.keys()) == sorted(expected_files.keys())
    for path, content in result_files.items():
        assert content == expected_files[path]


@pytest.mark.parametrize(
    "test_name, renderers",
    [("no_matching_mac_v2", Renderer.Netplan | Renderer.NetworkManager)],
)
def test_convert(test_name, renderers, tmp_path):
    network_config = safeyaml.load(
        Path(ARTIFACT_DIR, f"{test_name}.yaml").read_text()
    )
    network_state = parse_net_config_data(network_config["network"])
    if Renderer.Netplan in renderers:
        renderer = NetplanRenderer()
        expected_dir = ARTIFACT_DIR / test_name / "netplan"
        result_dir = tmp_path / "netplan"
    if Renderer.NetworkManager in renderers:
        renderer = NetworkManagerRenderer()
        expected_dir = ARTIFACT_DIR / test_name / "network_manager"
        result_dir = tmp_path / "network_manager"
    renderer.render_network_state(
        network_state, target=str(result_dir / test_name)
    )
    _assert_expected_config_file_artifacts(expected_dir, result_dir, test_name)
