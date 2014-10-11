#! /usr/bin/env python3
import sys
import os


class TextTransposer:
    """Suffix conventions: U implies input (untransposed), T implies
    output (transposed).  Hence rowsU == colsT and colsU == rowsT.
    """

    separator = b' '

    def __init__(self, fd_in, fd_out):
        self.fd_in = fd_in
        self.fd_out = fd_out
        self.rowU_tell = {} # seek here to get next value from within the row
        self.rowT = {}      # collect output
        self.collected_size = 0 # in bytes, ignoring python overhead

        # no data yet
        self.colsU = -1
        self.rowsU = -1
        self.longcell = 0       # without separator
        self.longrowU = 0       # with \n

    def rowsT(self):
        return self.colsU
    def colsT(self):
        return self.rowsU

    def loop_until_done(self):
        passnum = 0
        nextcolU = 0
        while True:
            nextcolU = self.loop(passnum, nextcolU)
            print("  next loop = %s" % nextcolU)
            if nextcolU == None:
                break
            passnum += 1

    def loop(self, passnum, colU_start):
        rowU = 0
        if passnum == 0:
            keep_colU = None    # init on first row
            self.rowU_tell[rowU] = self.fd_in.tell()
        else:
            self.fd_in.seek(self.rowU_tell[0])
            keep_colU = range(colU_start, self.colsU)
            print("    set keep_colU = %s" % keep_colU)

        while True:
            line = self.fd_in.readline()
            if line == b'':
                break           # eof
            print("  got line=%s, sep=%s" % (repr(line), self.separator))
            colsU = line.split(self.separator)
            colsU[-1] = colsU[-1].rstrip(b'\n')
            print("  colsU=(%s)" % repr(colsU))
            if passnum == 0:
                if self.colsU < 0:
                    # first row seen ever
                    self.colsU = len(colsU)
                    keep_colU = range(colU_start, int(self.colsU / 2))
                    print("    set keep_colU = %s" % keep_colU)
                elif len(colsU) != self.colsU:
                    raise Exception("%d: column count mismatch (got %d, expect %d)" %
                                    (rowU+1, len(colsU), self.colsU))
                rowU += 1
                self.rowU_tell[rowU] = self.fd_in.tell()
                longest = max(map(len, colsU))
                if longest > self.longcell:
                    self.longcell = longest
                if len(line) > self.longrowU:
                    self.longrowU = len(line)
            else:
                rowU += 1

            if rowU == 1:
                for x in keep_colU:
                    self.rowT[x]  = colsU[x] + self.separator
            else:
                for x in keep_colU:
                    self.rowT[x] += colsU[x] + self.separator

        print("    ready is %s" % self.rowT)
        for y in keep_colU:
            print("  write row %d" % y)
            self.fd_out.write( self.rowT[y] + b'\n' )
        self.rowT = {}
        print("  done loop %d, next is col %d" % (passnum, keep_colU.stop))
        return (keep_colU.stop, None)[keep_colU.stop == self.colsU]


def main():

    path_in = sys.argv[-1]
    path_out = os.path.basename(path_in)+'.transposed'
 
    with open(path_in,'rb') as fd_in, open(path_out, 'wb') as fd_out:
        transposer = TextTransposer(fd_in, fd_out)
        transposer.loop_until_done()

    return


if __name__ == '__main__':
    main()
