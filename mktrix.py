#! /usr/bin/env python3

import sys
import math

def main():
    args = sys.argv[1:]

    transposed = False
    if args != [] and args[0] == '-T':
        args.pop(0)
        transposed = True

    if args != []:
        raise Exception("junk: %s" % args)

    # original problem size
    width = range(0, 8)
    height = range(0, 10)

    # arbitrary functions along the edges
    edgeX = list(map(math.cos, width))
    edgeY = list(map(math.tan, height))

    
    def show(x,y):
        val = edgeX[x] + edgeY[y]
        # arbitrary formatting, just to make cell length irregular
        fmt = "%.5f"
        if val > 1.2:
            fmt = "%.3f"
        elif val > 3:
            fmt = "%.0f"
        if transposed:
            end = (' ','\n')[ y == height.stop - 1 ]
        else:
            end = (' ', '\n')[ x == width.stop - 1]
        print(fmt % val, end=end)

    if transposed:
        for x in width:
            for y in height:
                show(x,y)
    else:
        for y in height:
            for x in width:
                show(x,y)

if __name__ == '__main__':

    # from https://docs.python.org/3/library/profile.html#profile.Profile
#    import cProfile, pstats, io
#    pr = cProfile.Profile()
#    pr.enable()

    main()
