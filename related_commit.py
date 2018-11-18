import requests
import re
import bs4


class ChainOp():
    def __init__(self, o=None):
        self.o = o
        
    def map(self, func):
        if isinstance(self.o, list):
            self.o = [x for x in map(func, self.o) if x]
            
        return self
    
    def apply(self, func):
        self.o = func(self.o)
        return self
    
    def get(self):
        return self.o
    
    def copy(self):
        return ChainOp(self.o)

    def split(self, func):
        a = []
        b = []
        for i in self.o:
            if func(i):
                a.append(i)
            else:
                b.append(i)
        return ChainOp(a), ChainOp(b)
    
    def __add__(self, other):
        return ChainOp(self.o + other.o)
    
    def __len__(self):
        return len(self.o)
    
    def __str__(self):
        return str(o)
    
    def __repr__(self):
        return 'ChainOp(%s)' % (str(self.o), )
    
reg = re.compile(r'^/[\w\-]+/[\w\-]+/(commit|pull)/\w+$')
def case_timeline(bs):
    a = ChainOp().apply(lambda _: bs.find_all('div', class_='discussion-item'))
    b = a.copy()
    a = a.map(lambda x: x.find_all('h4', class_='discussion-item-ref-title'))\
             .map(lambda x: x[0].find('a', href=reg))
    b = b.map(lambda x: x.find('code'))\
         .map(lambda x: x.find('a', href=reg))
    return a + b
                
                
related_keywords = ['fix', 'solv', 'resolv', 'clos']
def case_dblock(bs):
    return ChainOp(bs.find_all('tr', class_='d-block'))\
             .map(lambda x: x.find_all('td', class_='d-block'))\
             .map(lambda x: x[0] if x[0].find('p') else None)\
             .map(lambda x: x.find('a', class_='commit-link') if any((w in x.p.text for w in related_keywords)) else None)


def get_all_related_commits_pulls(url):
    r = requests.get(url)
    text = r.content
    *_, owner, repo, method, number = r.url.split('/')
    bs = bs4.BeautifulSoup(text, 'html5lib')
    ass = case_timeline(bs) + case_dblock(bs)
    hrefs = ass.map(lambda x: x['href'])
    commits, pulls = hrefs.split(lambda x: 'commit' in x)

    def get_tail_intify(intify=False):
        def get_tail_id(x):
            xs = x.split('/')
            if intify:
                return xs[1], int(xs[-1])
            return xs[1], xs[-1]
        return get_tail_id

    commits, pulls = commits.map(get_tail_intify(False)).get(), pulls.map(get_tail_intify(True)).get()

    # FIXME why did I write these two line???
    # if method == 'pull':
    #     pulls.append((owner, int(number)))

    return commits, pulls, method == 'pull'


def main():
    url_1 = "https://github.com/tensorflow/tensorflow/issues/447"
    r = requests.get(url_1)
    text_1 = r.content

    url_2 = "https://github.com/tensorflow/tensorflow/issues/14169"
    r = requests.get(url_2)
    text_2 = r.content

    url_3 = "https://github.com/tensorflow/tensorflow/issues/20983"
    r = requests.get(url_3)
    text_3 = r.content

    assert len(case_timeline(bs4.BeautifulSoup(text_1, 'html5lib'))) == 6
    assert len(case_dblock(bs4.BeautifulSoup(text_2, 'html5lib')) ) == 2
    assert len(case_timeline(bs4.BeautifulSoup(text_3, 'html5lib'))) == 4

if __name__ == '__main__':
    main()