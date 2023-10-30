#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from tqdm import tqdm
import os
import numpy as np
from matplotlib.offsetbox import AnchoredText
import matplotlib.ticker as ticker
import matplotlib.pyplot as plt
from scipy.io.wavfile import read
from pathlib import Path
descr = """Custom Levelmeter for calibration of devices with a helmholz resonator

BASE LIB
calculations reviewed on 
04.01.2023
12.10.2023
 
AUTHOR: max scharf Di 24. Okt 14:18:40 CEST 2023 maximilian.scharf_at_uol.de
"""
__version__ = 1.1


class defaultSettings:
    widthTimeWindow = [35]  # in ms (35 is the optimum)
    stepTime = 0.5  # feed forward step size of time window as multiples of the time window width
    file = list(Path("./exampleSounds/").glob("*.wav"))
    target = "./tmp/{}.pdf"
    plot = True
    verbose = True
    resonanceWidth = 120  # Hz
    breakOnError = True
    individual = False
    individual_UnitsOfLevel = None
    individual_fLim = [100, 300]  # Hz
    individual_title = "{}"
    exportResults = True  # export to excel
    fullScale = True  # calculate in units of full scale; caution: if you have a mix of resolutions, calculating in dbFS will cause problems!
    calibrationOffset = 130  # use for calibration
    progressBar = True


defaults = defaultSettings()


def applyWin(signal, fs, tstart, twidth):
    """apply a time window operation to a time signal


    Parameters
    ----------
    signal : int16 Array
        time signal
    fs     : int
        samplingrate.
    tstart : float
        starting time of window in seconds
    twidth : float
        width of window in seconds.

    Returns
    -------
    -segment of the signal where the filter is nonzero
    -unshifted filter as array

    """
    dt = 1/fs  # time between samples in seconds
    posStart = int(tstart/dt)  # start of time windows in samples
    # width of window in samples; np.fft.rfft requires even sample number
    winLength = 2*(int(twidth/dt)//2)

    # window=np.hanning(winLength)
    window = np.ones(winLength)

    solution = window*signal[posStart:posStart+winLength:1]
    return solution, window


def analyze(args=defaults):

    # errocheck
    args.file = list(map(Path, args.file))  # turn into Paths
    if len(args.file) == 0:
        raise Exception("no soundfiles provided")
    if False in map(lambda x: x.suffix == ".wav", args.file):
        raise Exception("no .wav soundfiles provided")

    # prepare optional functions
    if args.exportResults:
        import pandas as pd

    if args.plot and len(args.file) > 0:
        fig, axs = plt.subplots(2)
    else:
        if args.verbose:
            print("plots are turned off")

    levelData = []
    dataDtypes = []

    if len(args.file) == 0:
        raise Exception("no soundfiles found")
    for tWidth in np.array(args.widthTimeWindow)*1e-3:
        try:
            for file in args.file:
                tStep = args.stepTime*tWidth
                fs, data = read(file)

                # count number of channels and make mono
                if len(np.shape(data)) > 1:
                    data = np.array([d[0] for d in data])

                # fullscaleValue
                fullScaleMaxVal = np.iinfo(data[0]).max
                dataDtypes.append(data.dtype)

                # remove DC
                data = data-np.mean(data)

                # instantaneous level at resonance frequency
                level = []

                # check where the maximum peak is located
                powSpec = abs(np.fft.rfft(data))**2/len(data)
                f = np.fft.rfftfreq(len(data), d=1/fs)
                fResonance = abs(f[np.argmax(powSpec)])

                tStartRange = np.arange(0, len(data)/fs-tWidth, tStep)
                for tStart in tqdm(tStartRange, desc=os.path.split(file)[1], disable=not args.verbose):
                    # apply time window
                    tmpS, filt = applyWin(data, fs, tStart, tWidth)
                    # powerspectrum real->hermitian->consider only pos frequency
                    # -> the actual power has to be twice as large
                    powSpecShort = abs(np.fft.rfft(
                        tmpS, norm="ortho"))**2*2/tWidth
                    fShort = np.fft.rfftfreq(len(tmpS), d=1/fs)
                    # level in the frequency interval
                    nMin = np.argmin(
                        abs(fShort-(fResonance-args.resonanceWidth/2)))-1
                    nMax = np.argmin(
                        abs(fShort-(fResonance+args.resonanceWidth/2)))
                    # append the power in the frequency interval
                    level.append(sum(powSpecShort[nMin:nMax]))

                # store in appropriate units
                if args.fullScale:
                    """calculate the maximum possible power that can be stored in
                    the time window.(fs =len(data)/(len(data)/fs))"""
                    refVal = fullScaleMaxVal**2*fs
                else:
                    refVal = fs  # dimensional reasons
                leveldB = 10 * \
                    np.log10([l/refVal for l in level])+args.calibrationOffset

                if args.plot:
                    # transient of instantaneous level
                    axs[0].plot(tStartRange, leveldB)
                    # max level over resonance frequency
                    axs[1].scatter(fResonance, max(leveldB),
                                   label=os.path.split(file)[1])
                    axs[0].set_title(
                        "considered resonance width={0:2.2f}Hz, "
                        "Time-window={1:3.1f}ms".format(args.resonanceWidth, tWidth*1000))
                    axs[0].set_xlabel("time /s")
                    axs[0].set_ylabel(
                        "level /dB{}".format("FS"*args.fullScale+""))

                levelData.append([Path(file).name, tWidth, max(leveldB),
                                 fResonance, fullScaleMaxVal, leveldB, fs])

        except Exception as inst:
            if args.breakOnError:
                # preserve prior stack trace
                raise
            else:
                print(
                    "\n\nerror [{}] while processing file [{}]".format(inst, file))

        # some stats
        lev = [l[2] for l in levelData]
        lMean = np.mean(lev)
        lStd = np.std(lev)
        if args.plot and len(levelData) > 0:
            axs[0].set_ylim(min(lev)-1, max(lev)+1)

            axs[1].set_ylabel(
                "maximum Level /dB{}".format("FS"*args.fullScale+" "))
            axs[1].set_xlabel("resonance frequency /Hz")

            axs[1].add_artist(AnchoredText("Level:\n"+r"$\mu$="+"{:2.2f}dB{}\n".format(lMean, "FS"*args.fullScale+" ") +
                                           r"$\sigma$="+"{0:2.2f}dB{1}".format(lStd, "FS"*args.fullScale+" "), loc="lower right"))
            plt.tight_layout()
            name = "TimeWin_{0:2.2f}ms_resWidth_{1:2.2f}Hz".format(
                tWidth, args.resonanceWidth)
            plt.savefig(args.target.format(name))
            plt.show()

    if args.verbose:
        print("filename\t\t\twindowsize\t\tmax Level"
              " /dB{}{}{}\t\t frequency /Hz".format("FS"*args.fullScale+" ", "+"*(args.calibrationOffset <= 0)+"-"*(args.calibrationOffset > 0), args.calibrationOffset))
        for p in levelData:
            if args.fullScale:
                print(
                    "{0}\t\t{1}/s\t\t{2:2.2f}dBFS\t\t{3:4.3f}Hz".format(*p[:-1]))
            else:
                print(
                    "{0}\t\t{1}/s\t\t{2:2.2f}dB\t\t{3:4.3f}Hz".format(*p[:-1]))

        print("mean power across all soundfiles in the resonance frequency interval\nl\t={0:2.2f}±{1:2.2f}dB{2}\nstd\t={3:2.2f}dB{2}".format(
            lMean, lStd/np.sqrt(len(lev)), "FS"*args.fullScale+" ", lStd))

        print("data read as {}".format(set(dataDtypes)))
        if len(set(dataDtypes)) > 1:
            print("Warning: data is not stored in a consitent bit depth")

        # calculate the level in units of dB

    # plot everything individually
        if args.individual:
            for p in levelData:
                plt.plot(p[-1])
                plt.suptitle("mean-maximum level={0:2.2f}".format(lMean-p[2]))
                plt.savefig(args.target.format(
                    "individual"+"_"+Path(p[0]).stem))

    res = {"fileName": [d[0] for d in levelData],
           "tWidth": [d[1] for d in levelData],
           "max/dB{}".format("FS"*args.fullScale+""*(not args.fullScale)): [d[2] for d in levelData],
           "fRes": [d[3] for d in levelData],
           "fullScaleMaxVal": [d[4] for d in levelData],
           "leveldB": [d[5] for d in levelData],
           "samplingRate": [d[6] for d in levelData], }

    # store data for further analysis
    if args.exportResults:
        df = pd.DataFrame(res)
        path = Path(args.target.format("exportedResults"))
        df.to_excel(path.with_suffix(".xlsx"))
        df.to_pickle(path.with_suffix(".pickle"))

    # return levelData
    return res

# %%


if __name__ == "__main__":
    # show an example of how this works
    Path(defaultSettings.target).parent.mkdir(exist_ok=True)
    dat = analyze(defaultSettings)
