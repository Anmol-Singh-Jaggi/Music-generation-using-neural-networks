#!/usr/bin/env python2
import os
from pprint import pprint
import cPickle as pickle
import datetime
import errno
# hehehe

import numpy as np
from keras.models import Sequential, model_from_json
from keras.layers.recurrent import LSTM
from keras.layers.core import Dense, Dropout
from keras.regularizers import l2


from midi_lib.midi_sequence import midi_to_sequence, sequence_to_midi
from midi_lib.midi_volume import insert_volume_into_state_matrix, remove_volume_from_state_matrix
from midi_lib.midi_compress import compress_state_matrix, decompress_state_matrix


def load_data():
    """
    Loads midi files and outputs the concatenated state-matrix.
    :returns: The state-matrix
    :return_type: 2-D list
    """
    state_matrix = []
    for subdir, dirs, files in os.walk('music'):
        for file in files:
            print 'Loading "' + file + '" ...\n'
            file_path = os.path.join(subdir, file)
            state_matrix.extend(midi_to_sequence(file_path)[0])
            print 'Done!\n'
    return state_matrix


def preprocess_data(state_matrix, prime_size):
    """
    Processes the 2-D state-matrix to produce a 3-D version 'X'
    of dimensions = len(state_matrix) * prime_size * len(state_matrix[0]).
    Each 2-D row 'X[i]' becomes a separate datapoint.
    X[i][tick][pitch] = volume
    Corresponding to each datapoint X[i], a target value Y[i] is also computed.
    :param state_matrix: The state-matrix.
    :type state_matrix: 2-D list
    :param prime_size: The size of a single datapoint
    :type prime_size: int
    :returns: A list of datapoints and the corresponding target output values.
    :return_type: (3-D list, 2-D list)
    """
    X = []
    Y = []

    # Skip (step_size - 1) rows while forming the input dataset to save memory.
    step_size = 1

    for i in xrange(0, len(state_matrix) - prime_size, step_size):
        data_point_x = state_matrix[i: i + prime_size]
        X.append(data_point_x)

        data_point_y = state_matrix[i + prime_size]
        Y.append(data_point_y)

    return X, Y


# Location for saving (serializing) the model.
model_save_dir = os.path.join('models', 'model_save')
model_arch_path = os.path.join(model_save_dir, 'arch.json')
model_weights_path = os.path.join(model_save_dir, 'weights.h5')
model_history_path = os.path.join(model_save_dir, 'hist.p')


def save_model(model):
    """
    Saves (serializes) the model.
    Mostly adapted from Keras documentation.
    :param model: The model to save.
    :type model: Keras model type
    :returns: None.
    """
    def mkdir_p(path):
        """
        Create all the intermediate directories in a path.
        Similar to the `mkdir -p` command.
        """
        try:
            os.makedirs(path)
        except OSError as exc:  # Python >2.5
            if exc.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else:
                raise

    # Ensure that the directory exists!
    mkdir_p(model_save_dir)

    json_string = model.to_json()

    open(model_arch_path, 'w').write(json_string)
    model.save_weights(model_weights_path)


def load_model():
    """
    Loads (deserializes) the model.
    Mostly adapted from Keras documentation.
    :returns: None.
    :return_type: Keras model type
    """
    model = model_from_json(open(model_arch_path).read())
    model.load_weights(model_weights_path)
    return model


def main():
    boolean_on = False
    compression_on = True

    print 'Loading data ...\n'
    state_matrix = load_data()
    print 'Loading data done!\n'
    # print len(state_matrix)

    if compression_on:
        print 'Compressing ...\n'
        row_comp_ratio = 10
        print 'Row-compression ratio = ', row_comp_ratio
        state_matrix, columns_present = compress_state_matrix(
            state_matrix, row_comp_ratio)
        print 'Compressing done!\n'

    if boolean_on:
        print 'Converting to boolean ...\n'
        volume_avg = remove_volume_from_state_matrix(state_matrix)
        print 'Converting to boolean done!\n'
        print 'Average volume = ', volume_avg, '\n\n'

    prime_size = 50
    print 'Preprocessing data ...\n'
    X, Y = preprocess_data(state_matrix, prime_size)
    print 'Preprocessing data done!\n'

    print 'Casting to numpy-array ...\n'
    if boolean_on:
        X, Y = np.array(X, dtype=bool), np.array(Y, dtype=bool)
    else:
        X, Y = np.array(X), np.array(Y)
    print 'Casting to numpy-array done!\n'

    print X.shape, Y.shape, '\n'

    if os.path.exists(model_save_dir):
        print 'Loading model ...\n'
        model = load_model()
        print 'Loading model done!\n'
    else:
        print 'Building model ...\n'

        min_nodes = 128
        nb_nodes = max(X.shape[2], min_nodes)

        model = Sequential()
        print 'Adding layer 1 ...\n'
        model.add(LSTM(nb_nodes, input_shape=(
            X.shape[1], X.shape[2]), return_sequences=True))
        model.add(Dropout(0.2))
        print 'Adding layer 2 ...\n'
        model.add(LSTM(nb_nodes * 2))
        model.add(Dropout(0.2))
        print 'Adding layer 3 ...\n'
        model.add(Dense(X.shape[2]))
        model.add(Dropout(0.2))

        print 'Building model done!\n'

    print 'Compiling model ...\n'
    model.compile(loss='mean_squared_error',
                  optimizer="rmsprop", metrics=['accuracy'])
    print 'Compiling model done!\n'

    if not os.path.exists(model_save_dir):
        print 'Training model ...\n'
        history = model.fit(X, Y, validation_split=0.2)
        print 'Training model done!\n'
        # pickle.dump(history, open(model_history_path, 'wb'))

        print 'Saving model ...\n'
        save_model(model)
        print 'Saving model done!\n'

    print 'Predicting ...\n'
    predictions = model.predict(X, batch_size=32, verbose=1)
    print 'Predicting done!\n'
    print predictions.shape

    print 'Post-processing predictions ...\n'

    if boolean_on:
        predictions = np.around(predictions).astype(int).clip(min=0)
    else:
        predictions = predictions.astype(int).clip(min=0)

    # Converting back to python-list from numpy-array
    predictions = predictions.tolist()

    if boolean_on:
        print 'Converting from boolean ...\n'
        insert_volume_into_state_matrix(predictions, volume_avg)
        print 'Converting from boolean done!\n'

    if compression_on:
        print 'Decompressing ...\n'
        predictions = decompress_state_matrix(predictions, columns_present)
        print 'Decompressing done!\n'

    print 'Post-processing predictions done!\n'

    print 'Writing to output file ...\n'
    out_file_path = 'output/' + \
        str(datetime.datetime.now()).replace(
            ' ', '_').replace(':', '_') + '.mid'
    sequence_to_midi(predictions, out_file_path, (100, None))
    print 'Writing to output file done!\n'


if __name__ == '__main__':
    main()
