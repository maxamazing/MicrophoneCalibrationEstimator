#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 27 16:33:16 2023

show how this tool works

@author: max scharf Mo 13. Feb 16>30>01 CET 2023 maximilian.scharf_at_uol.d
"""
import pygraphviz as pgv


g = pgv.AGraph()
#g.graph_attr["label"] = "calibration with bottles"
g.node_attr["shape"] = "rectangle"
g.edge_attr["dir"] = "forward"

g_rec = "record 3 long continuous \nsounds on provided bottle\nat armlength/50cm distance"
g_peakfind = "peakfinder"
g.add_edge(g_rec, g_peakfind, label=" fft")

g_freqCheck = "is the resonance\nfrequency in the\naccepted range?"
g.add_edge(g_peakfind, g_freqCheck)
g.add_edge(g_freqCheck, g_rec, label=" no")

g_powerSpec = "calculate\npowerspectrum"
g.add_edge(g_rec, g_powerSpec, label=" stfft\n(time-window)")

g_meanPow = "power in\nfrequency interval\naround resonance\n(filter width)"
g.add_edge(g_powerSpec, g_meanPow)
g.add_edge(g_freqCheck, g_meanPow, label=" yes:\n continue")
g.add_edge(g_peakfind, g_meanPow)

g_findMax = "find the maximum\nvalue for the recoding"
g.add_edge(g_meanPow, g_findMax, label=" level\n in dB")

g_subtr = "subtract result\nfrom empirical 92.8 dB SPL"
g.add_edge(g_findMax, g_subtr)

g_result = "estimate of level correction"
g.add_edge(g_subtr, g_result)


g.layout("dot")

formatExt = "png"
g.draw(path="./workingPrinciple."+formatExt, format=formatExt)
