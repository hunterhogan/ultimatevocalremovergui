# Copyright (c) Facebook, Inc. and its affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
"""Loading pretrained models.
"""

import logging
from pathlib import Path
import typing as tp

from Dora.log import fatal

import logging

from diffq import DiffQuantizer
import torch.hub

from .model import Demucs
from .tasnet_v2 import ConvTasNet
from .utils import set_state

from .hdemucs import HDemucs
from .repo import RemoteRepo, LocalRepo, ModelOnlyRepo, BagOnlyRepo, AnyModelRepo, ModelLoadingError  # noqa

logger = logging.getLogger(__name__)
ROOT_URL = "https://dl.fbaipublicfiles.com/demucs/mdx_final/"
REMOTE_ROOT = Path(__file__).parent / 'remote'

SOURCES = ["drums", "bass", "other", "vocals"]


def demucs_unittest():
    model = HDemucs(channels=4, sources=SOURCES)
    return model


def add_model_flags(parser):
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("-s", "--sig", help="Locally trained XP signature.")
    group.add_argument("-n", "--name", default="mdx_extra_q",
                       help="Pretrained model name or signature. Default is mdx_extra_q.")
    parser.add_argument("--repo", type=Path,
                        help="Folder containing all pre-trained models for use with -n.")


def _parse_remote_files(remote_file_list) -> tp.Dict[str, str]:
    """Parses a list of remote files and returns a dictionary of model names and their corresponding URLs."""
    root: str = ''
    models: tp.Dict[str, str] = {}
    for line in remote_file_list.read_text().split('\n'):
        line = line.strip()
        if line.startswith('#'):
            continue
        elif line.startswith('root:'):
            root = line.split(':', 1)[1].strip()
        else:
            sig = line.split('-', 1)[0]
            assert sig not in models
            models[sig] = ROOT_URL + root + line
    return models

def get_model(name: str,
              repo: tp.Optional[Path] = None):
    """`name` must be a bag of models name or a pretrained signature
    from the remote AWS model repo or the specified local repo if `repo` is not None.
    """
    if name == 'demucs_unittest':
        return demucs_unittest()
    model_repo: ModelOnlyRepo
    if repo is None:
        models = _parse_remote_files(REMOTE_ROOT / 'files.txt')
        model_repo = RemoteRepo(models)
        bag_repo = BagOnlyRepo(REMOTE_ROOT, model_repo)
    else:
        if not repo.is_dir():
            fatal(f"{repo} must exist and be a directory.")
        model_repo = LocalRepo(repo)
        bag_repo = BagOnlyRepo(repo, model_repo)
    any_repo = AnyModelRepo(model_repo, bag_repo)
    model = any_repo.get_model(name)
    model.eval()
    return model

def get_model_from_args(args):
    """
    Load local model package or pre-trained model.
    """
    return get_model(name=args.name, repo=args.repo)


logger = logging.getLogger(__name__)
ROOT = "https://dl.fbaipublicfiles.com/demucs/v3.0/"

PRETRAINED_MODELS = {
    'demucs': 'e07c671f',
    'demucs48_hq': '28a1282c',
    'demucs_extra': '3646af93',
    'demucs_quantized': '07afea75',
    'tasnet': 'beb46fac',
    'tasnet_extra': 'df3777b2',
    'demucs_unittest': '09ebc15f',
}

SOURCES = ["drums", "bass", "other", "vocals"]


def get_url(name):
    """
    Get the URL for a pretrained model.

    Parameters:
        name (str): The name of the pretrained model.

    Returns:
        str: The URL for the pretrained model.
    """
    sig = PRETRAINED_MODELS[name]
    return ROOT + name + "-" + sig[:8] + ".th"

def is_pretrained(name):
    """
    Check if a model is pretrained.

    Parameters:
        name (str): The name of the model.

    Returns:
        bool: True if the model is pretrained, False otherwise.
    """
    return name in PRETRAINED_MODELS


def load_pretrained(name):
    """
    Load a pretrained model.

    Parameters:
        name (str): The name of the pretrained model.

    Returns:
        torch.nn.Module: The loaded pretrained model.
    """
    if name == "demucs":
        return demucs(pretrained=True)
    elif name == "demucs48_hq":
        return demucs(pretrained=True, hq=True, channels=48)
    elif name == "demucs_extra":
        return demucs(pretrained=True, extra=True)
    elif name == "demucs_quantized":
        return demucs(pretrained=True, quantized=True)
    elif name == "demucs_unittest":
        return demucs_unittest(pretrained=True)
    elif name == "tasnet":
        return tasnet(pretrained=True)
    elif name == "tasnet_extra":
        return tasnet(pretrained=True, extra=True)
    else:
        raise ValueError(f"Invalid pretrained name {name}")


def _load_state(name, model, quantizer=None):
    """
    Load the state of a pretrained model.

    Parameters:
        name (str): The name of the pretrained model.
        model (torch.nn.Module): The model to load the state into.
        quantizer (optional): The quantizer to use for quantized models.
    """
    url = get_url(name)
    state = torch.hub.load_state_dict_from_url(url, map_location='cpu', check_hash=True)
    set_state(model, quantizer, state)
    if quantizer:
        quantizer.detach()


def demucs_unittest(pretrained=True):
    """
    Unittest function for Demucs model.

    This function creates an instance of the Demucs model with 4 channels and pre-defined sources.
    Optionally, it loads pre-trained weights for the model.

    Parameters:
        pretrained (bool, optional): If True, load pre-trained weights. Defaults to True.

    Returns:
        Demucs: An instance of the Demucs model.
    """
    model = Demucs(channels=4, sources=SOURCES)
    if pretrained:
        _load_state('demucs_unittest', model)
    return model


def demucs(pretrained=True, extra=False, quantized=False, hq=False, channels=64):
    """
    Create an instance of the Demucs model.

    This function creates an instance of the Demucs model with customizable options such as the number of channels.
    Optionally, it loads pre-trained weights based on the specified options.

    Parameters:
        pretrained (bool, optional): If True, load pre-trained weights. Defaults to True.
        extra (bool, optional): If True, enable extra options. Defaults to False.
        quantized (bool, optional): If True, use quantized weights. Defaults to False.
        hq (bool, optional): If True, use high-quality weights. Defaults to False.
        channels (int, optional): Number of channels for the model. Defaults to 64.

    Returns:
        Demucs: An instance of the Demucs model.

    Raises:
        ValueError: If extra or quantized is True and pretrained is False.
        ValueError: If more than one of extra, quantized, hq is True.
    """
    if not pretrained and (extra or quantized or hq):
        raise ValueError("if extra or quantized is True, pretrained must be True.")
    model = Demucs(sources=SOURCES, channels=channels)
    if pretrained:
        name = 'demucs'
        if channels != 64:
            name += str(channels)
        quantizer = None
        if sum([extra, quantized, hq]) > 1:
            raise ValueError("Only one of extra, quantized, hq, can be True.")
        if quantized:
            quantizer = DiffQuantizer(model, group_size=8, min_size=1)
            name += '_quantized'
        if extra:
            name += '_extra'
        if hq:
            name += '_hq'
        _load_state(name, model, quantizer)
    return model


def tasnet(pretrained=True, extra=False):
    """
    Create an instance of the ConvTasNet model.

    This function creates an instance of the ConvTasNet model with customizable options.
    Optionally, it loads pre-trained weights based on the specified options.

    Parameters:
        pretrained (bool, optional): If True, load pre-trained weights. Defaults to True.
        extra (bool, optional): If True, enable extra options. Defaults to False.

    Returns:
        ConvTasNet: An instance of the ConvTasNet model.

    Raises:
        ValueError: If extra is True and pretrained is False.
    """
    if not pretrained and extra:
        raise ValueError("if extra is True, pretrained must be True.")
    model = ConvTasNet(X=10, sources=SOURCES)
    if pretrained:
        name = 'tasnet'
        if extra:
            name = 'tasnet_extra'
        _load_state(name, model)
    return model

