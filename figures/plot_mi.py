import pandas as pd
import numpy as np
import matplotlib
from matplotlib import rc
matplotlib.use
import matplotlib.pyplot as plt
plt.style.use('ggplot')
rc('font', **{'family': 'serif', 'serif': ['Computer Modern']})
rc('text', usetex=True)
import argparse
from pdb import set_trace as st


def plot_mis(csv, comparing_cols, title, roll=20):
    df = pd.read_csv(csv) \
           .replace(np.inf, np.NaN) \
           .interpolate(method='linear')
    colors = ['b','g','r','c','m','y','k','w','burlywood']
    plt.figure()
    ax = plt.subplot(111)
    
    for col_map, color in zip(comparing_cols, colors):
        column, name = col_map
        col = df[column]
        ma = col.rolling(roll).mean()
        mstd = col.rolling(roll).std()
        plt.plot(ma.index, ma, color, label=name)
        plt.fill_between(mstd.index, ma - 2 * mstd, ma + 2 * mstd,
                     color=color, alpha=0.2)
        plt.title(title)
        plt.xlabel('Step')
        plt.ylabel('Bits')
        ax.legend()
    plt.show()


parser = argparse.ArgumentParser()
parser.add_argument("--measure", help="Entropy based measures: {entropy: 'h', "
                "joint entropy: 'jh', "
                "mutual information: 'mi', "
                "conditional mutual information: 'cmi'}")
parser.add_argument("--in_csv", help="Input csv file name")
parser.add_argument("--title", help="Title of the figure", default=None)
parser.add_argument("--roll", help="Rolling mean window (default: 20).",
                    type=int, default=20)
args = parser.parse_args()

column_map, posfijo = {'h':
        ([("$H[h(Z, Z)]$", "H(Z)"), ("$H[h(Y, Y)]$", "H(Y)"), ("$H[h(X, X)]$", "H(X)")], "HX_HY_HZ"),
                   'cmi':
        ([("$I[h(Y+Z, X)]$", "I(Y,Z|X)"), ("$I[h(X+Z, Y)]$", "I(X,Z|Y)"), ("$I[h(X+Y, Z)]$", "I(X,Y|Z)")], "IXYZ_IYZX_IXZY"),
                    'mi':
        ([("$I[h(Y, X)]$", "I(X,Y)"), ("$I[h(Z, X)]$", "I(Z,X)"), ("$I[h(Z, Y)]$", "I(Y,Z)")], "IXY_IYZ_IXZ"),
                    'jh':
        ([("$H[h(Y+Z, Y+Z)]$", "H(Y,Z)"), ("$H[h(X+Z, X+Z)]$", "H(X,Z)"), ("$H[h(X+Y, X+Y)]$", "H(X,Y)")], "HXY_HYZ_HZX")
    }[args.measure]
title = args.title if args.title is None \
            else "Entropy-Based measure: " + posfijo
plot_mis(csv=args.in_csv, comparing_cols=column_map, title=title, roll=args.roll)

