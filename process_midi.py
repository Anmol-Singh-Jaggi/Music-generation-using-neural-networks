#!/usr/bin/env python2
import midi
from copy import copy
from pprint import pprint


def compress_state(state):
    ret = []
    for pitch, volume in enumerate(state):
        if volume > 0:
            ret.append(pitch)
    return ret


def compress_state_matrix(state_matrix):
    ret = ""
    for idx, state in enumerate(state_matrix):
        ret += str(idx) + ".) " + str(compress_state(state)) + "\n"
    return ret


def load_midi(filepath):
    state_matrix = []
    state = [0] * 128

    pattern = midi.read_midifile(filepath)
    pprint(pattern)

    for event in pattern[0]:
        if isinstance(event, midi.EndOfTrackEvent):
            break
        elif isinstance(event, midi.NoteEvent):
            if event.tick > 0:
                state_matrix += event.tick * [copy(state)]
            if isinstance(event, midi.NoteOffEvent) or event.data[1] == 0:
                state[event.pitch] = 0
            else:
                state[event.pitch] = event.data[1]

    return state_matrix


def get_next_different_state(state_matrix, index):
    for i in xrange(index + 1, len(state_matrix)):
        if state_matrix[i] != state_matrix[index]:
            return i
    return len(state_matrix)


def state_diff(current_state, next_state):
    notes_on = []
    notes_off = []

    for pitch, (volume1, volume2) in enumerate(zip(current_state, next_state)):
        if volume1 == 0 and volume2 > 0:
            notes_on.append([pitch, volume2])
        elif volume1 > 0 and volume2 == 0:
            notes_off.append([pitch, volume2])

    return (notes_on, notes_off)


def dump_midi(state_matrix, filepath):
    pattern = midi.Pattern()
    track = midi.Track()
    pattern.append(track)

    # Append the very first tick
    notes_on, _ = state_diff([0] * 128, state_matrix[0])
    for note in notes_on:
        track.append(midi.NoteOnEvent(tick=0, channel=0, data=note))

    # Append the rest of the ticks
    current_state_index = 0
    while current_state_index < len(state_matrix):
        next_state_index = get_next_different_state(
            state_matrix, current_state_index)
        ticks_elapsed = next_state_index - current_state_index

        current_state = state_matrix[current_state_index]
        next_state = state_matrix[next_state_index] if next_state_index < len(
            state_matrix) else [0] * 128
        notes_on, notes_off = state_diff(current_state, next_state)

        for note in notes_on:
            track.append(midi.NoteOnEvent(
                tick=ticks_elapsed, channel=0, data=note))
            ticks_elapsed = 0

        for note in notes_off:
            track.append(midi.NoteOffEvent(
                tick=ticks_elapsed, channel=0, data=note))
            ticks_elapsed = 0

        current_state_index = next_state_index

    track.append(midi.EndOfTrackEvent(tick=1))
    midi.write_midifile(filepath, pattern)

    return pattern


def main():
    filepath = 'music/debug.mid'
    state_matrix = load_midi(filepath)
    print compress_state_matrix(state_matrix)
    print '\n' * 5
    pattern = dump_midi(state_matrix, 'out.mid')
    pprint(pattern)


if __name__ == '__main__':
    main()
