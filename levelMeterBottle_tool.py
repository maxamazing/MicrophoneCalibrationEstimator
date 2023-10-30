#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse as argparse
import numpy as np
import levelMeterBottle as lm
from pathlib import Path
import sys
descr = """A Levelmeter for the calibration of mobile devices with a helmholz resonator

USER TOOL:

    provide one or more recordings of different people blowing on the same type of beer bottle
    with the same recording device at 50cm/ one armlength distance. The should be 3 long
    and continuous sounds of the resonating bottle at the fundamental frequency.

    The tool will produce an estimate of the calibration offset to transform the recoded levels
    to dB SPL. This offset has to be added to the recorded level in dB to yield dB SPL. An estimate
    of the uncertainty is also produced as standard deviation.

AUTHOR: max scharf 04.01.2023 CEST 2023 maximilian.scharfatuol.de
LICENSE: GNU GPLv3 
"""

if __name__ == "__main__":
    def boolToText(inp):
        if inp:
            return "store_false"
        else:
            return "store_true"

    fRes = [160, 180]
    parser = argparse.ArgumentParser(
        add_help=True, formatter_class=argparse.RawDescriptionHelpFormatter, description=descr)
    parser.add_argument("-w", "--widthTimeWindow", nargs="*", default=lm.defaults.widthTimeWindow,
                        help="width of the time window in ms. "
                        "default={}".format(lm.defaults.widthTimeWindow),
                        type=float)
    parser.add_argument("-s", "--stepTime", default=lm.defaults.stepTime,
                        help="feed forward step size of time window as multiples of the time"
                        " window width. Default={}".format(lm.defaults.stepTime),
                        type=float)
    parser.add_argument("-v", "--verbose", action=boolToText(False),
                        help="show the output results in the terminal"
                        " default= {}".format(False))
    parser.add_argument("-r", "--resonanceWidth", default=lm.defaults.resonanceWidth,
                        help="rectangular width of the considered resonance. "
                        "default={}Hz".format(lm.defaults.resonanceWidth),
                        type=float)
    parser.add_argument("file", nargs="*",
                        help="required: paths to .wav soundfiles that you want to process.")
    parser.add_argument("-f", "--fullScale", action=boolToText(lm.defaults.fullScale),
                        help="calculate the calibration factor relative to to the fullscale"
                        " signal. default={}".format(lm.defaults.fullScale))
    parser.add_argument("-pr", "--progressBar", action=boolToText(lm.defaults.progressBar),
                        help="display a progressbar. default={}".format(lm.defaults.progressBar))
    parser.add_argument("-fr", "--frequencyRange", nargs=2, default=fRes,
                        help="permitted frequency range for resonance frequency. default={}".format(
                            fRes),
                        type=float)
    # hide some settings from the user
    args = parser.parse_args()
    args.calibrationOffset = 0
    args.individual = False
    args.exportResults = False
    args.target = None
    args.breakOnError = False
    args.plot = False

    try:
        dat = lm.analyze(args)
    except Exception as ex:
        parser.print_help()
        sys.exit(ex)

    # offset relative to fullscale or absolute value?
    if args.fullScale:
        key = "max/dBFS"
    else:
        key = "max/dB"

    blackList = np.array([f < args.frequencyRange[0] or f >
                          args.frequencyRange[1] for f in dat["fRes"]])
    if True in blackList:
        print("\n\nWarning: resonance frequency condition not fulfilled: f not within ({0:3.1f},{1:3.1f})Hz".format(
            *args.frequencyRange))
        for name, fRes in zip(np.array(dat['fileName'])[blackList], np.array(dat["fRes"])[blackList]):
            print("\t file: {0}: \tfRes={1:3.2f}".format(name, fRes))
        print("{} valid files remain.".format(sum(~blackList)))

    levelList = np.array(dat[key])[~blackList]

    if len(levelList) > 0:
        level = np.mean(levelList)
        num = len(levelList)

        """3 dB as empirical variance/sqrt of independent measurements 
        +0.5 dB calibration uncertainty of original levelmeter
        independent uncertainties add quadratically"""
        levelStd = np.sqrt(3**2/num+0.5**2)

        print("\nresults:\n\t{0} independent measurements assumed\n\tcalibration offset\t\t={1:2.2f} dB\n\testimated standard deviation\t={2:2.2f} dB".format(
            num, 92.79-level, levelStd))
    else:
        print("\n No valid soundfiles")
        sys.exit(0)
