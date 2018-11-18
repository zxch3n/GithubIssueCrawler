import os
import json

def _extract_filename(file):
    return file['filename']


def get_related_files_from_commit(commit):
    return map(_extract_filename, commit['files'])


def get_related_files_from_pull(pull):
    return map(_extract_filename, (x for commit in pull['commits'] for x in commit['files']))
        

def get_related_files(issue):
    files = ['[C]' + x for commit in issue['related_commits'] for x in get_related_files_from_commit(commit) ]
    files.extend(['[P]' + x for pull in issue['related_pulls'] for x in get_related_files_from_pull(pull) ])
    return set(files)


def read_line_json(path):
    with open(path, encoding='utf-8') as f:
        data = []
        for i, line in enumerate(f):
            d = json.loads(line[:-1])
            data.append(d)
    return data