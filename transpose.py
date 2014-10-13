#! /usr/bin/env python3
import sys
import os
import warnings


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
        self.shortrowU = -1     # with \n
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

            # get file size -- from http://stackoverflow.com/a/19079887
            self.fd_in.seek(0, os.SEEK_END)
            self.fd_in_size = self.fd_in.tell()
            self.fd_in.seek(self.rowU_tell[rowU], os.SEEK_SET)
        else:
            self.fd_in.seek(self.rowU_tell[0])
            keep_colU = range(colU_start, min(self.colsU, colU_start + self.colU_keepn))
            print("    set keep_colU = %s" % keep_colU)

        while True:
            line = self.fd_in.readline()
            if rowU % 10000 == 0:
                print("  rowU:%d" % rowU)
            if line == b'':
                break           # eof
            colsU = line.split(self.separator)
            if colsU[0] == b'':
                # leading space on the row
                colsU.pop(0)
            colsU[-1] = colsU[-1].rstrip(b'\n')
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
                if self.shortrowU == -1 or len(line) < self.shortrowU:
                    self.shortrowU = len(line)
                    print("    shortrow:%d" % self.shortrowU)
                if len(line) > self.longrowU:
                    self.longrowU = len(line)
                    print("    longrow:%d" % self.longrowU)
                longest = max(map(len, colsU))
                rowU += 1
                if longest > self.longcell:
                    self.longcell = longest
                    keep_colU = self.set_memlimit(keep_colU, self.est_rowsU(rowU))
                elif rowU % 1000 == 0:
                    keep_colU = self.set_memlimit(keep_colU, self.est_rowsU(rowU))
                self.rowU_tell[rowU] = self.fd_in.tell()
            else:
                rowU += 1

            self.stash_rowU(rowU, keep_colU, colsU)

        if passnum == 0:
            self.rowsU = rowU
        self.dump_kept(keep_colU)
        if passnum == 0:
            # re-evaluate, now we have a real rowsU
            self.rowsU = rowU
            self.set_memlimit(keep_colU, rowU)
            if self.colU_keepn == 1:
                mib = 1024*1024.0
                warnings.warn("Streaming only! Memory budget (%.3f MiB) insufficient for one row (up to %.3f MiB from colsT:%d * longcell:%d bytes)" %
                              (self.mem_budget / mib, self.bytes_per_rowT / mib, self.colsT(), self.longcell))

        print("  done loop %d, next is col %d" % (passnum, keep_colU.stop))
        return (keep_colU.stop, None)[keep_colU.stop == self.colsU]

    def est_rowsU(self, curr_rowU):
        """During first pass, estimate rowsU count from available data.
        Early over-estimates may reduce the useful work done by passnum == 0.
        Might do better counting actual memory usage, or bytes stashed in rowT[]."""
        fpos = self.fd_in.tell()
        min_rows = self.fd_in_size / self.longrowU
        seen_frac = fpos / self.fd_in_size
        if seen_frac < 0.25:
            # near start of file => inaccurate stats, give a low estimate
            return max(int(min_rows), curr_rowU)
        else:
            avglen_rows = curr_rowU * 1.0 * self.fd_in_size / fpos
            # max_rows = self.fd_in_size / self.shortrowU
            return max(int(avglen_rows), curr_rowU)

    def stash_rowU(self, rowU, keep_colU, colsU):
        stashable = range(keep_colU.start + 1, keep_colU.stop)
        # We don't stash colsU[keep_colU.start], because we can stream
        # it during reading.  Still, keep it in the range to simplify
        # other logic / not yet refactored
        if rowU == 1:
            for x in stashable:
                self.rowT[x] = [ colsU[x] ]
        else:
            self.fd_out.write(self.separator) # non-stashed
            for x in stashable:
                self.rowT[x].append(colsU[x])
        self.fd_out.write(colsU[keep_colU.start]) # non-stashed

    def dump_kept(self, keep_colU):
        self.fd_out.write(b'\n') # close the non-stashed output
        widthT = range(0, self.colsT())
        lastT = self.colsT() - 1
        stashable = range(keep_colU.start + 1, keep_colU.stop)
        for y in stashable:
            for x in widthT:
                self.fd_out.write(self.rowT[y][x])
                self.fd_out.write((self.separator, b'\n')[ x == lastT ])
        self.rowT = {}

    def set_memlimit(self, keep_colU, rowsU):
        """Longest cell (longcell) was increased.  We may need to store fewer
        colsU == rowsT in stay in memory budget."""
        bytes_per_rowT = (self.longcell + 1) * rowsU # +1 for sep
        self.bytes_per_rowT = bytes_per_rowT
        old_colU_keepn = self.colU_keepn
        new_colU_keepn = int(self.mem_budget / bytes_per_rowT
                             / 1.67) # empirical fudge factor, Python 3.3.2 on x86_64
        self.colU_keepn = min(old_colU_keepn,
                              new_colU_keepn + 1) # +1 for the non-stashed
        if new_colU_keepn != old_colU_keepn:
            print("      set_memlimit(%s, %.3f MiB, rowsU:%d) bytes_per_rowT:%d for longcell:%d gives colU:%d" %
                  (keep_colU, self.mem_budget / (1024*1024.0), rowsU,
                   bytes_per_rowT, self.longcell, self.colU_keepn))
        if self.colU_keepn >= old_colU_keepn:
            # plenty, continue
            # new_colU_keepn could be larger than current, but that won't bring rowT[] elements back
            return keep_colU
        else:
            # time to downsize
            purge = range(self.colU_keepn, keep_colU.stop)
            if self.rowT != {}: # nothing to purge yet, if we're called on first row
                print("      purge rowT[%s]" % purge)
                for x in purge:
                    del self.rowT[x]
            return range(keep_colU.start, self.colU_keepn)

def main():

    path_in = sys.argv[-1]
    path_out = os.path.basename(path_in)+'.transposed'
 
    with open(path_in,'rb') as fd_in, open(path_out, 'wb') as fd_out:
        transposer = TextTransposer(fd_in, fd_out)
        transposer.loop_until_done()

    return


if __name__ == '__main__':

    # from https://docs.python.org/3/library/profile.html#profile.Profile
    import cProfile, pstats, io
    pr = cProfile.Profile()
    pr.enable()

    main()

    pr.disable()
    s = io.StringIO()
    sortby = 'cumulative'
    ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    ps.print_stats()
    print(s.getvalue())
