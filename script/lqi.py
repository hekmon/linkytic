"""
This script demonstrates the low-pass filter used by the link quality indicator sensor. Its goal is to be tuned to alert
the used when most of the data is not properly received (e.g less than 30%) and be immune to transient interferences.
A recursive (or Infinite Impulse Response) filter is the best memory/computing efficient."""

# pip install matplotlib numpy

import matplotlib.pyplot as plt
import numpy as np

if __name__ == "__main__":

    X_LEN = 100

    x = np.round(np.random.random(X_LEN))
    # x = np.zeros(X_LEN)
    # x = np.ones(X_LEN)

    y_it = np.zeros(x.shape)

    y0 = 1

    alpha = 1/16

    for i, x_it in enumerate(x):

        y_it[i] = y0 * (1 - alpha) + x_it * alpha
        y0 = y_it[i]


    plt.plot(x)
    plt.plot(y_it)
    plt.show()