#! /usr/bin/perl

package Transposer;

use strict;
use warnings;

use IO::Handle;
use List::Util qw( min max );


=head1 NAME

Transposer - matrix transpose for large non-sparse textual-cell file

=head1 CONVENTIONS

Suffix conventions: U implies input (untransposed), T implies
output (transposed).  Hence rowsU == colsT and colsU == rowsT.

=cut

sub main {
  my ($pkg, $in) = @_;
  my ($out) = $in =~ m{(?:^|/)([^/]+)$} # unix-centric
    or die "can't get leaf of $in";
  $out .= '.transposed';

  open my $fh_in, '<', $in or die "Read $in: $!";
  open my $fh_out, '>', $out or die "Write $out: $!";

  my $transposer = $pkg->new($fh_in, $fh_out);
  $transposer->loop_until_done();
  return;
}

sub new {
  my ($pkg, $fd_in, $fd_out) = @_;

  my $self =
    { fd_in => $fd_in,
      fd_out => $fd_out,
      rowU_tell => [], # seek here to get next value from within the row
      rowT => {},      # collect output
      mem_budget => 100 * 1024 * 1024, # in bytes, ignoring overhead & rowU_tell
      separator => ' ',

      # no data yet
      colsU => -1,
      rowsU => -1,
      longcell => 0,            # without separator
      longrowU => 0,            # with \n
      shortrowU => -1,          # with \n
      colU_keepn => -1,
    };
  bless $self, $pkg;
  return $self;
}

sub rowsT { $_[0]->{colsU} }
sub colsT { $_[0]->{rowsU} }

sub _init {
  my ($pkg) = @_;
  foreach my $prop (qw( colsU rowsU colU fd_in fd_out longcell longrowU shortrowU separator ),
                    qw( bytes_per_rowT ), # init in set_memlimit
                    qw( rowT colU_keepn rowU_tell fd_in_size mem_budget )) {
    my $code = sub {
      my ($self, @set) = @_;
      ($self->{$prop}) = @set if @set;
      return $self->{$prop};
    };
    no strict 'refs';
    *{"${pkg}::$prop"} = $code;
  }
  return;
}


sub loop_until_done {
  my ($self) = @_;
  my $passnum = 0;
  my $nextcolU = 0;
  while (1) {
    $nextcolU = $self->loop($passnum, $nextcolU);
    printf "  next loop = %s\n", defined $nextcolU ? $nextcolU : 'None';
    last unless defined $nextcolU;
    $passnum ++;
  }
  return;
}

sub loop {
  my ($self, $passnum, $colU_start) = @_;
  my $rowU = 0;
  my $keep_colU; # init on first row, or subsequent pass
  my ($need_widthU, $need_bytes);

  if ($passnum == 0) {
    $self->rowU_tell->[$rowU] = $self->fd_in->tell();
    $self->fd_in_size(-s $self->fd_in);
  } else {
    $self->fd_in->seek($self->rowU_tell->[0], 0)
      or die "seek failed: $!";

    $keep_colU = Range->new($colU_start, min($self->colsU, $colU_start + $self->colU_keepn));
    $need_widthU = $keep_colU->size;
    $need_bytes = ($self->longcell + 1) * $need_widthU;
    printf "    set keep_colU = %s\n", $keep_colU->to_string;
  }

  if ($passnum == 0) {
    while (1) {
      printf "  rowU:%d\n", $rowU unless $rowU % 10000;
      my $line = $self->fd_in->getline;
      last unless defined $line; # eof

      my @colsU;
      if ($self->colsU < 0) {
        # first row seen ever
        @colsU = split $self->separator, $line;
        shift @colsU while $colsU[0] eq ''; # leading space on the row
        chomp $colsU[-1];

        $self->colsU(scalar @colsU);
        $self->colU_keepn(scalar @colsU); # initially keep all
        $keep_colU = Range->new($colU_start, $self->colsU);
        printf "    set keep_colU = %s\n", $keep_colU->to_string;
      } else {
        $need_widthU = $keep_colU->size;
        # XXX: here we used to check actual #colsU matched expected (check matrix not ragged)
        # now we only discover where lines are short
        @colsU = split $self->separator, $line, $need_widthU + 1;
        pop @colsU; # the unwanted tail
        # XXX: using Perl built-in means we aren't checking $need_widthU columns are available
        chomp $colsU[-1]; # has effect only on last column
      }

      if ($self->shortrowU == -1 || length($line) < $self->shortrowU) {
        $self->shortrowU(length($line));
        printf "    shortrow:%d\n", $self->shortrowU;
      }
      if (length($line) > $self->longrowU) {
        $self->longrowU(length($line));
          printf "    longrow:%d\n", $self->longrowU;
      }

      my $longest = max(map { length($_) } @colsU);
      $rowU ++;
      if ($longest > $self->longcell) {
        $self->longcell($longest);
        $keep_colU = $self->set_memlimit($keep_colU, $self->est_rowsU($rowU));
      } elsif ($rowU % 1000 == 0) {
        $keep_colU = $self->set_memlimit($keep_colU, $self->est_rowsU($rowU));
      }
      $self->rowU_tell->[$rowU] = $self->fd_in->tell();
      $self->stash_rowU($rowU, $keep_colU, \@colsU);
    }

  } else {
    while (1) {
      printf "  rowU:%d\n", $rowU unless $rowU % 10000;
      last if $rowU == $self->rowsU; # eof
      $self->fd_in->seek($self->rowU_tell->[$rowU], 0)
        or die "seek failed: $!";
      my $txt;
      my $nread = $self->fd_in->read($txt, $need_bytes);
      die "$rowU: $! on input" unless defined $nread;
      my @colsU = split $self->separator, $txt, $need_widthU + 1;
      pop @colsU; # the unwanted tail
      $rowU ++;
      $self->stash_rowU($rowU, $keep_colU, \@colsU);
    }
  }

  $self->rowsU($rowU) if $passnum == 0;
  $self->dump_kept($keep_colU);
  if ($passnum == 0) {
    # re-evaluate, now we have a real rowsU
    $self->set_memlimit($keep_colU, $rowU);
    if ($self->colU_keepn == 1) {
      my $mib = 1024*1024;
      warn sprintf("Streaming only! Memory budget (%.3f MiB) insufficient for one row (up to %.3f MiB from colsT:%d * longcell:%d bytes)",
                   $self->mem_budget / $mib,
                   $self->bytes_per_rowT / $mib,
                   $self->colsT, $self->longcell);
    }
  }

  printf "  done loop %d, next is col %d\n", $passnum, $keep_colU->stop;

  return $keep_colU->stop == $self->colsU ? undef : $keep_colU->stop;
}

# sub splitn : not required

# During first pass, estimate rowsU count from available data.
# Early over-estimates may reduce the useful work done by passnum == 0.
# Might do better counting actual memory usage, or bytes stashed in rowT[].
sub est_rowsU {
  my ($self, $curr_rowU) = @_;
  my $fpos = $self->fd_in->tell();
  my $min_rows = $self->fd_in_size / $self->longrowU;
  my $seen_frac = $fpos / $self->fd_in_size;
  if ($seen_frac < 0.25) {
    # near start of file => inaccurate stats, give a low estimate
    return max(int($min_rows), $curr_rowU);
  } else {
    my $avglen_rows = $curr_rowU * $self->fd_in_size / $fpos;
    # max_rows = self.fd_in_size / self.shortrowU
    return max(int($avglen_rows), $curr_rowU);
  }
}

sub stash_rowU {
  my ($self, $rowU, $keep_colU, $colsU_l) = @_;
  my @stashable = Range->new($keep_colU->start + 1, $keep_colU->stop)->incl;
  # We don't stash colsU[0], because we can stream
  # it during reading.  Still, keep it in the range to simplify
  # other logic / not yet refactored
  print { $self->fd_out } $self->separator unless $rowU == 1; # non-stashed, sep before
  my $rT = $self->rowT;
  my $kcUs = $keep_colU->start;
  foreach my $x ($stashable[0] .. $stashable[1]) {
    push @{ $rT->{$x} }, $colsU_l->[ $x - $kcUs ];
  }
  my $nonstash = $colsU_l->[0]; # non-stashed
  print { $self->fd_out } $nonstash;
  $self->rowU_tell->[ $rowU-1 ] += length($nonstash) + 1; # +1 for sep after
  return;
}

sub dump_kept {
  my ($self, $keep_colU) = @_;
  my $fd_out = $self->fd_out;
  my $sep = $self->separator;
  my $rUt = $self->rowU_tell;
  my $rT = $self->rowT;
  my @widthT = Range->new(0, $self->colsT)->incl;
  my $lastT = $self->colsT - 1;
  my @stashable = Range->new($keep_colU->start + 1, $keep_colU->stop)->incl;


  print {$fd_out} "\n"; # close the non-stashed output
  foreach my $y (@stashable[0] .. $stashable[1]) {
    foreach my $x ($widthT[0] .. $widthT[1]) {
      my $cell = $rT->{$y}[$x];
      $rUt->[$x] += length($cell) + 1; # +1 for sep
      print {$fd_out} $cell, $x == $lastT ? "\n" : $sep;
    }
  }
  $self->rowT({});
  return;
}

# Longest cell (longcell) was increased.  We may need to store fewer
# colsU == rowsT in stay in memory budget.
sub set_memlimit {
  my ($self, $keep_colU, $rowsU) = @_;
  my $bytes_per_rowT = ($self->longcell + 1) * $rowsU; # +1 for sep
  $self->bytes_per_rowT($bytes_per_rowT);
  my $old_colU_keepn = $self->colU_keepn;
  my $new_colU_keepn = int($self->mem_budget / $bytes_per_rowT
                           / 1.00); # XXX: empirical fudge factor ..?
  $self->colU_keepn( min($old_colU_keepn, $new_colU_keepn + 1) ); # =1 for the non-stashed
  if ($new_colU_keepn != $old_colU_keepn) {
    printf "      set_memlimit(%s, %.3f MiB, rowsU:%d) bytes_per_rowT:%d for longcell:%d gives colU:%d\n",
      $keep_colU->to_string, $self->mem_budget / (1024*1024), $rowsU,
        $bytes_per_rowT, $self->longcell, $self->colU_keepn;
  }
  if ($self->colU_keepn >= $old_colU_keepn) {
    # plenty, continue
    # new_colU_keepn could be larger than current, but that won't bring rowT[] elements back
    return $keep_colU;
  } else {
    # time to downsize
    my $purge = Range->new($self->colU_keepn, $keep_colU->stop);
    if (keys %{ $self->rowT }) {
      printf "      purge rowT[%s]\n", $purge->to_string;
      foreach my $i ($purge->start .. $purge->stop - 1) {
        delete ${ $self->rowT }{ $i };
      }
    } # else nothing to purge yet, we're called on first row
    return Range->new($keep_colU->start, $self->colU_keepn);
  }
}


__PACKAGE__->_init;
__PACKAGE__->main(@ARGV) unless caller();

1;



package Range;
sub new {
  my ($pkg, $start, $stop) = @_;
  return bless [ $start, $stop ], $pkg;
}

sub incl {
  my ($self) = @_;
  die unless wantarray;
  return ($self->[0], $self->[1] - 1);
}

sub start { $_[0][0] }
sub stop  { $_[0][1] }

sub size  {
  my ($self) = @_;
  return $self->stop - $self->start;
}

sub to_string {
  my ($self) = @_;
  return sprintf('[%d, %d)', # Interval notation
                 $self->start, $self->stop);
}

1;
