#!/usr/bin/env python2
'''
Compress state matrix and back.
'''
from midi_debug import *
from midi_sequence import *
import operator

def compress_rows(state_matrix, batch_size):
    def compute_batch_average(state_matrix, start_idx, end_idx):
        ret = [0] * len(state_matrix[0])

        for i in xrange(start_idx, end_idx):
            for j in xrange(len(ret)):
                ret[j] += state_matrix[i][j]

        for i in xrange(len(ret)):
            ret[i] /= end_idx - start_idx

        return ret

    def compute_batch_mode(state_matrix, start_idx, end_idx):
        ret = [0] * len(state_matrix[0])
        note_dict = [{} for i in xrange(len(state_matrix[0]))]
        
        for i in xrange(start_idx, end_idx):
            for j in xrange(len(ret)):
            	if state_matrix[i][j] in note_dict[j].keys():
            		note_dict[j][state_matrix[i][j]] += 1
            	else:
            		note_dict[j][state_matrix[i][j]] = 1

        for i in xrange(len(ret)):
            ret[i] = max(note_dict[i].iteritems(), key=operator.itemgetter(1))[0]

        return ret

    ret = []

    for i in xrange(0, len(state_matrix), batch_size):
        batch_mode_row = compute_batch_mode(state_matrix, i, min(i + batch_size, len(state_matrix)))
        ret.append(batch_mode_row)

    return ret


def transpose(grid):
    return map(list, zip(*grid))


def compress_state_matrix(state_matrix, row_compression_batch_size=0):
    ret = []
    columns_present = []

    if row_compression_batch_size:
        state_matrix = compress_rows(state_matrix, row_compression_batch_size)

    state_matrix_transposed = transpose(state_matrix)

    for idx, pitch_column in enumerate(state_matrix_transposed):
        if not all(volume == 0 for volume in pitch_column):
            ret.append(list(pitch_column))
            columns_present.append(idx)

    ret = transpose(ret)

    return ret, columns_present


def decompress_state_matrix(state_matrix, columns_present):
    ret = [[0] * 128] * len(state_matrix)
    ret = transpose(ret)

    state_matrix_transposed = transpose(state_matrix)

    for idx, col in enumerate(columns_present):
        ret[col] = list(state_matrix_transposed[idx])

    ret = transpose(ret)

    return ret


def main():
    filepath = 'debug.mid'
    state_matrix, _ = midi_to_sequence(filepath)

    print desparsify_state_matrix(state_matrix)
    print '\n\n\n'

    state_matrix_compressed, columns_present = compress_state_matrix(
        state_matrix)
    print desparsify_state_matrix(state_matrix_compressed)
    print '\n\n\n'
    print columns_present
    print '\n\n\n'

    state_matrix_decompressed = decompress_state_matrix(
        state_matrix_compressed, columns_present)
    print desparsify_state_matrix(state_matrix_decompressed)
    print '\n\n\n'

    assert(state_matrix == state_matrix_decompressed)

    batch_size = 60
    print len(state_matrix)
    state_matrix_row_compressed = compress_rows(state_matrix, batch_size)
    print len(state_matrix_row_compressed)
    print len(state_matrix_row_compressed) * batch_size
    print '\n\n\n'


if __name__ == '__main__':
    main()
