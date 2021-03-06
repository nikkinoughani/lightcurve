#!/usr/bin/env python

import os
import sys
import pyfits
import numpy
import scipy.stats

import subprocess
import sqlite3

from create_table import read_colunms_from_param_file
from get_lightcurve import get_lightcurve

import argparse




if __name__ == "__main__":

    database_file = sys.argv[1]
    sex_param_file = sys.argv[2]

    min_nphot = int(sys.argv[3])
    
    start_at = int(sys.argv[4])
    end_at = int(sys.argv[5])

    output_file = sys.argv[6]

    #print database_file, sex_param_file


    columns = read_colunms_from_param_file(sex_param_file)
    db = sqlite3.connect(database_file)
    
    #
    #
    #
    sql = "SELECT sourceid FROM sources WHERE nphot >= %d LIMIT %d" % (
        min_nphot, end_at)
    cursor = db.cursor()
    query = cursor.execute(sql)
    results = numpy.array(query.fetchmany(size=end_at))

    print "all ready to go"

    column_header = [
        'source-id',
        'mean-mag',
        'median_mag',
        'mean_error',
        'max_mag', 'min_mag',
        'skewness', 'kurtosis',
        '16% percentile', '84% percentile',
        '2.5% percentile', '97.5% percentile',
        'median_error',
        'median of sigma clipped errors',
        'mean of sigma clipped errors',
        'sigma-clipped median', 'sigma-clipped 1-sigma',
        ]
    column_head = "\n".join(["column %02d: %s" % (i+1,s) for i,s in enumerate(column_header)])

    source_stats = []
    for i, sourceid in enumerate(results[start_at:end_at+1]):

        sys.stdout.write("\rComputing stats for source %d of %d" % (i, end_at-start_at+1))
        sys.stdout.flush()

        result = get_lightcurve(
            database=db,
            sourceid=sourceid,
            sextractor_columns=columns,
            calibrate=True,
        )
        if (result is None):
            print "nothing found"
            continue

        lightcurve, sqlquery, query_columns, diffphot = result
        #print lightcurve

        magnitudes = lightcurve[:,8]
        errors = lightcurve[:,13]
        flags =lightcurve [:,24]
        #print magnitudes


        mean_mag = numpy.mean(magnitudes)
        median_mag = numpy.median(magnitudes)
        mean_error = numpy.mean(errors)
        median_error = numpy.median(errors)

        max_mag = numpy.max(magnitudes)
        min_mag = numpy.min(magnitudes)

        kurtosis = scipy.stats.kurtosis(magnitudes)
        skewness = scipy.stats.skew(magnitudes)

        #valid = numpy.zeros(magnitudes.shape, dtype=bool)
        valid = (magnitudes > 10) & (magnitudes < 30) & (flags < 0.7)
        _median, _sigma = -1, -1
        for i in range(3):
            if (numpy.sum(valid) <= 1):
                break
            _s = numpy.percentile(magnitudes[valid], [16,84,50])
            _median = _s[2]
            _sigma = 0.5*(_s[1]-_s[0])
            _min = _median - 3*_sigma
            _max = _median + 3*_sigma
            bad = (magnitudes > _max) | (magnitudes < _min)
            valid[bad] = False

        sigmas = numpy.percentile(magnitudes, [16,84,2.5,97.5])
        source_stats.append(
            [sourceid, mean_mag, median_mag, mean_error, max_mag, min_mag, 
             skewness, kurtosis, sigmas[0], sigmas[1], sigmas[2], sigmas[3], 
             median_error, numpy.median(errors[valid]), numpy.mean(errors[valid]), _median, _sigma])

        _source_stats = numpy.array(source_stats)
        numpy.savetxt(output_file, _source_stats, header=column_head)

    source_stats = numpy.array(source_stats)

    numpy.savetxt(output_file, source_stats, header=column_head)

    #if ((max_mag-min_mag) > 3*mean_error):
    #    print "interesting"
    #else:
    #    print "boring"
