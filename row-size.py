#! /usr/bin/env python3
import sys
import os

def main():
    path_in = sys.argv[-1]
    sys.stderr.write("# sizes include \\n\n")
    sys.stderr.flush()
    totln = 0
    with open(path_in) as fd_in:
        while True:
            line = fd_in.readline()
            if line == '':
                break
            totln += len(line)
            print("%3d (%4d): %s" % (len(line),totln, line), end='')
    return


if __name__ == '__main__':
    main()
