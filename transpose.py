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
        self.mem_budget = 100 * 1024 * 1024 # in bytes, ignoring Python overheads & rowU_tell

        # no data yet
        self.colsU = -1
        self.rowsU = -1
        self.longcell = 0       # without separator
        self.longrowU = 0       # with \n
        self.colU_keepn = -1

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
            keep_colU = range(colU_start, min(self.colsU, colU_start + self.colU_keepn))
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
                    self.colU_keepn = self.colsU # initially keep all
                    keep_colU = range(colU_start, self.colsU)
                    print("    set keep_colU = %s" % keep_colU)
                elif len(colsU) != self.colsU:
                    raise Exception("%d: column count mismatch (got %d, expect %d)" %
                                    (rowU+1, len(colsU), self.colsU))
                longest = max(map(len, colsU))
                if longest > self.longcell:
                    self.longcell = longest
                    keep_colU = self.set_memlimit(keep_colU)
                    print("    longcell:%d => colU_keepn:%d" % (longest, self.colU_keepn))
                if len(line) > self.longrowU:
                    self.longrowU = len(line)
                    print("    longrow:%d" % self.longrowU)
                rowU += 1
                self.rowU_tell[rowU] = self.fd_in.tell()
            else:
                rowU += 1

            if rowU == 1:
                for x in keep_colU:
                    self.rowT[x]  = colsU[x]
            else:
                for x in keep_colU:
                    self.rowT[x] += self.separator + colsU[x]

        print("    ready is %s" % self.rowT)
        for y in keep_colU:
            print("  write row %d" % y)
            self.fd_out.write( self.rowT[y] + b'\n' )
        self.rowT = {}
        print("  done loop %d, next is col %d" % (passnum, keep_colU.stop))
        return (keep_colU.stop, None)[keep_colU.stop == self.colsU]

    def set_memlimit(self, keep_colU):
        """Longest cell (longcell) was increased.  We may need to store fewer
        colsU == rowsT in stay in memory budget."""
        bytes_per_rowT = (self.longcell + 1) * self.rowsT() # +1 for sep
        new_colU_keepn = int(self.mem_budget / bytes_per_rowT)
        print("      set_memlimit(%s, %.3f MiB) bytes_per_rowT:%d for longcell:%d gives %d colU" %
              (keep_colU, self.mem_budget / (1024*1024.0), bytes_per_rowT, self.longcell, new_colU_keepn))
        if new_colU_keepn >= self.colU_keepn:
            # plenty, continue
            return keep_colU
        elif new_colU_keepn < 1:
            # this implemention doesn't support streaming one row at a
            # time, it will always buffer it
            mib = 1024*1024.0
            raise Exception("Memory budget (%.3f MiB) insufficient for one row (up to %.3f MiB from longcell:%d bytes)" %
                            (self.mem_budget / mib, bytes_per_rowT / mib, self.longcell))
        else:
            # time to downsize
            purge = range(new_colU_keepn, keep_colU.stop)
            if self.rowT != {}: # nothing to purge yet, if we're called on first row
                for x in purge:
                    print("      dropped rowT[%d] = %s" % (x, self.rowT[x]))
                    del self.rowT[x]
            self.colU_keepn = new_colU_keepn
            return range(keep_colU.start, new_colU_keepn)

def main():

    path_in = sys.argv[-1]
    path_out = os.path.basename(path_in)+'.transposed'
 
    with open(path_in,'rb') as fd_in, open(path_out, 'wb') as fd_out:
        transposer = TextTransposer(fd_in, fd_out)
        transposer.loop_until_done()

    return


if __name__ == '__main__':
    main()
