from github import Github
from itertools import chain
from collections import deque
from art import text2art, art
import os
from threading import Lock
from time import sleep, time
from functools import wraps
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import warnings
from github import Issue, Repository, IssueEvent, Commit, File, PullRequest
import related_commit
import github
import json

DEBUG = False


class GithubCrawl():
    def __init__(self):
        self.g = None

    def login(self, index=0):
        with open('user.info.json') as f:
            user = json.load(f)

        username = user[index]['user_name']
        self.g = Github(username, user[index]['password'])
        try:
            self._test_login()
        except github.GithubException as e:
            print("Please comfirm your username and password are correct in the user.info.json file.")
            print("======================================")
            raise e
        return self.g

    def _test_login(self):
        self.g.get_user('xx')

    def get_issues(self, owner, repo):
        user = self.g.get_user(owner)
        repo = user.get_repo(repo)
        issues = repo.get_issues()
        return issues


class MIssue:
    def __init__(self, issue, related_commits=None, related_pulls=None, is_pull=None):
        super().__init__()
        assert isinstance(issue, Issue.Issue)
        self.issue = issue
        self.related_commits = related_commits
        self.related_pulls = related_pulls
        self.is_pull = is_pull


def default_json_decode(o):
    if isinstance(o, MIssue):
        return {
            'is_pull': o.is_pull,
            'title': o.issue.title,
            'url': o.issue.url,
            'body': o.issue.body,
            'related_commits': o.related_commits,
            'related_pulls': o.related_pulls,
        }

    if isinstance(o, Commit.Commit):
        author = o.author.__dict__ if o.author is not None else {}
        return {
            'files': o.files,
            'url': o.url,
            'sha': o.sha,
            'stats': o.stats.raw_data,
            'author': author.get('name', None),
            'author_login_name': author.get('login', None),
            'author_url': author.get('html_url', None)
        }

    if isinstance(o, File.File):
        return {
            'additions': o.additions,
            'changes': o.changes,
            'deletions': o.deletions,
            'previous_filename': o.previous_filename,
            'sha': o.sha,
            'filename': o.filename,
            'status': o.status
        }

    if isinstance(o, PullRequest.PullRequest):
        raise NotImplementedError()

    return str(o)


def extract_pull_info(pull):
    commits = []
    for commit in pull.get_commits():
        commits.append(commit)

    return {
        'url': pull.html_url,
        'labels': [x.name for x in pull.labels],
        'body': pull.body,
        'commits': commits
    }


def get_all_refered_commit_id(issue) -> list:
    events = issue.get_events()
    commit_ids = []
    for event in events:
        if event.commit_id is not None:
            commit_ids.append(event.commit_id)

    return commit_ids


def get_issues(repo):
    assert isinstance(repo, Repository.Repository)
    _labels = list(repo.get_labels())

    def label_filter(x):
        desc = x.description
        x = x.name.lower()
        if 'bug' in x and 'debug' not in x:
            return True

        if desc is not None and 'bug' in x:
            return True

        return False

    labels = list(filter(label_filter, _labels))
    if len(labels) == 0:
        origin_list = ','.join([x.name for x in _labels])
        raise ValueError('Cannot find any bug related labels ' + origin_list)

    if len(labels) == 1:
        issue = repo.get_issues(state='closed', labels=labels)
        return issue, issue.totalCount

    raise NotImplementedError('Does not support multi-labels yet ' + ','.join([x.name for x in labels]))
    issue_list = []
    total_count = 0
    for label in labels:
        issue = repo.get_issues(state='closed', labels=[label])
        issue_list.append(issue)
        total_count += issue.totalCount
    issues = chain(*issue_list)
    return issues, total_count


def get_repo(g, owner, repo_name):
    user, repo = None, None
    try:
        user = g.get_user(owner)
        repo = user.get_repo(repo_name)
    except github.UnknownObjectException as e:
        if user is None:
            warnings.warn("User(%s) is not found" % (owner,), UserWarning)
        elif repo is None:
            warnings.warn("Repo(%s/%s) is not found" % (owner, repo_name), UserWarning)
        raise e
    return repo


def get_commit(g, owner, repo_name, commit_sha):
    repo = get_repo(g, owner, repo_name)
    try:
        commit = repo.get_commit(commit_sha)
    except github.UnknownObjectException as e:
        warnings.warn("Repo(%s/%s)'s commit<%s> is missing" % (owner, repo_name, commit_sha), UserWarning)
        raise e
    return commit


def get_pull(g, owner, repo_name, pull_number):
    repo = get_repo(g, owner, repo_name)
    try:
        pull = repo.get_pull(pull_number)
    except github.UnknownObjectException as e:
        warnings.warn("Repo(%s/%s)'s pull<%s> is missing" % (owner, repo_name, pull_number), UserWarning)
        raise e
    return pull


def get_missue(g, issue, repo):
    repo_name = repo.name
    owner = repo.owner.login
    commit_shas, pull_numbers, is_pull = related_commit.get_all_related_commits_pulls(issue.html_url)
    commits = []
    pulls = []
    for t_owner, commit_sha in commit_shas:
        if t_owner == owner:
            commit = repo.get_commit(commit_sha)
            commits.append(commit)
        else:
            try:
                commit = get_commit(g, t_owner, repo_name, commit_sha)
                commits.append(commit)
            except github.UnknownObjectException:
                pass

    for t_owner, pull_number in pull_numbers:
        if t_owner == owner:
            pull = repo.get_pull(pull_number)
            pulls.append(extract_pull_info(pull))
        else:
            try:
                pull = get_pull(g, owner, repo_name, pull_number)
                pulls.append(extract_pull_info(pull))
            except github.UnknownObjectException:
                pass

    return MIssue(issue, commits, pulls, is_pull)


def repeat_3times_if_failed(func):
    @wraps(func)
    def new_func(*args, **kwargs):
        times = 3
        while times:
            try:
                value = func(*args, **kwargs)
                return value
            except Exception as e:
                if DEBUG:
                    raise e
                else:
                    warnings.warn(str(e), UserWarning)
            times -= 1
            sleep(0.5)
        return None

    return new_func


def get_file_lines(path):
    n = 0
    if not os.path.exists(path):
        return 0

    with open(path) as f:
        for _ in f:
            n += 1
    print("File % s already exist, start crawling from index %d" % (path, n))
    return n


class TimeRecorder:
    def __init__(self, lag=300):
        self.times = deque()
        self.start_time = time()
        self.lag = lag

    def update(self, used_time):
        self.times.append(used_time)

    def used_time(self):
        return time() - self.start_time

    def left_time(self, left_num, thread_num=1):
        times = self.times
        if left_num == 0 or len(times) < 2:
            return -1, -1

        while times[-1] - times[0] > self.lag:
            times.popleft()
            if len(times) == 0:
                return -1, -1

        avg_speed = sum(times) / len(times)
        return avg_speed, left_num * avg_speed / thread_num


def crawl(owner, repo_name):
    print(text2art('CRAWL 4 TB') + '\n\n')
    print(art('random'))
    print(text2art(owner + '/' + repo_name))

    c = GithubCrawl()
    g = c.login(0)
    print(art('random'))
    print('Log in succeeded\n')
    repo = g.get_user(owner).get_repo(repo_name)
    issues, n = get_issues(repo)
    save_file_name = '%s.%s.json' % (owner, repo_name)
    if DEBUG:
        save_file_name = 'DEBUG.' + save_file_name
    already_saved_nums = get_file_lines(save_file_name)
    count_q = [None for _ in range(already_saved_nums)]
    time_recorder = TimeRecorder()
    thread_num = 10
    lock = Lock()
    print(art('random'))
    print('Start Crawling! Data will be saved to %s\n' % (save_file_name,))

    @repeat_3times_if_failed
    def work(_issue):
        nonlocal count_q, lock, time_recorder
        start = time()
        missue = get_missue(g, _issue, repo)
        with lock:
            with open(save_file_name, 'a', encoding='utf-8') as f:
                s = json.dumps(missue, default=default_json_decode)
                f.write(s)
                f.write('\n')
            count_q.append(None)
            used_time = time() - start
            time_recorder.update(used_time)
            avg, left_time = time_recorder.left_time(n - len(count_q), thread_num)
            print(f'{len(count_q)}/{n} '
                  f'[c:{len(missue.related_commits)},'
                  f'p:{len(missue.related_pulls)},'
                  f'n:{missue.issue.number}] '
                  f'used: {used_time * 1.0:.4},'
                  f'total: {time_recorder.used_time() * 1.0:.6},'
                  f'avg_speed: {avg * 1.0:.4},'
                  f'left: {left_time * 1.0:.5}')

    if not DEBUG:
        issues = issues[already_saved_nums:]
        with ThreadPoolExecutor(max_workers=thread_num) as worker:
            for _ in worker.map(work, issues):
                pass
    else:
        list(map(work, issues))


if __name__ == '__main__':
    crawl('Microsoft', 'TypeScript')
    # crawl('pytorch', 'glow')
