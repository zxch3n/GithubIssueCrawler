import numpy as np
import pandas as pd
import json 
import seaborn as sns
import nltk 
import matplotlib.pyplot as plt
from collections import defaultdict
from utils import *


class Issue:
    def __init__(self, data):
        self.body = data['body']
        self.url = data['url']
        self.title = data['title']
        self.id = int(self.url.split('/')[-1])
        self.files = get_related_files(data)
        self.commits = data['related_commits']
        self.pulls = data['related_pulls']
        
    def __eq__(self, o):
        if not isinstance(o, Issue):
            return False
        return self.title == o.title
    
    def __hash__(self):
        return hash(self.url)
    
    def __repr__(self):
        return 'Issue(id=%d, title="%s", url="%s")' % \
                (self.id, self.title, self.url)

class File:
    def __init__(self, name):
        self.name = name
        self.cissues = []
        self.pissues = []
    
    def update(self, issue, ftype):
        if ftype.startswith('[C]'):
            self.cissues.append(issue)
        elif ftype.startswith('[P]'):
            self.pissues.append(issue)
            
    def __hash__(self):
        return hash(self.name)
    
    def __eq__(self, o):
        if not isinstance(o, File):
            return False
        return self.name == o.name
    
    def __repr__(self):
        return "File(pr=%d, commit=%d, path=\"%s\")" % \
            (len(self.pissues), len(self.cissues), self.name)


def main():
    data = read_line_json('Microsoft.TypeScript.json')
    file_num = [len(get_related_files(issue)) for issue in data]
    large_file_num_issues = [issue for issue in data if len(get_related_files(issue)) > 100]
    issues = [Issue(d) for d in data]
    files = reverse_index_files(issues)

    save_files = {
        filename: {
            'Commit': [str(x) for x in file.cissues],
            'PR': [str(x) for x in file.pissues],
        }
        for filename, file in files.items()}

    with open("files.json", 'w', encoding='utf-8') as f:
        json.dump(save_files, f, indent=2)
        

if __name__ == '__main__':
    main()
