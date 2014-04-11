
import web
import os
import time
import glob
import subprocess
import json

web.config.debug = True

urls = (
    '/', 'IndexHandler',
    '/documentation', 'DocumentationHandler',
    '/bugs', 'BugsHandler',
    '/edit-bug/(.*)', 'EditBugHandler',
    '/new-bug', 'NewBugHandler',
    '/bug-editor', 'BugEditorHandler',
    '/save-bug', 'SaveBugHandler',
    '/contact', 'ContactHandler',
)

app = web.application(urls, globals())

if web.config.debug:
    if web.config.get('_session') is None:
        session = web.session.Session(app, web.session.DiskStore('sessions'))
        web.config._session = session
    else:
        session = web.config._session
        def debug_session_processor(handler):
            result = handler()
            web.config._session = session
            return result
        app.add_processor(debug_session_processor)
else:
    session = web.session.Session(app, web.session.DiskStore('sessions'))

def flashMessageProcessor(handler):
    result = handler()
    session.flashMessage = ''
    return result
    
app.add_processor(flashMessageProcessor)

def flashMessage(message):
    session.flashMessage = message

render = web.template.render("templates/",
                             globals = {'session': session})

timeFormat = '%Y-%m-%d_%H:%M:%S'

class Comment:
    def __init__(self, date, author, content):
        self.date = date
        self.author = author.strip()
        self.content = content.strip()
        
    def formatDate(self):
        return time.strftime(timeFormat, self.date)
        
    def formatDateUi(self):
        return time.strftime('%Y-%m-%d %H:%M:%S', self.date)        
        
def stripConcat(acc):
    if len(acc) == 0:
        return ""
    firstLine = None
    lastLine = None
    index = 0
    for line in acc:
        if firstLine == None and line.strip() != "":
            firstLine = index
        lastLine = index
        index += 1
    lastLine += 1
    acc = acc[firstLine:lastLine]
    return "\n".join(acc)
    
def handleState(result, acc, state):
    content = stripConcat(acc)
    if state == "id":
        result.id = content
    elif state == "title":
        result.title = content
    elif state == "assignee":
        result.assignee = content
    elif state == "status":
        result.status = content
    elif state.startswith("comment"):
        stateContent = state.split(' ')
        result.comments.append(Comment(time.strptime(stateContent[2], timeFormat),
                                       stateContent[1],
                                       content))

class Bug:
    @staticmethod
    def deserialize(text):
        lines = text.split("\n")
        result = Bug(None, None, None, None, [])
        state = ""
        acc = []
        for line in lines:
            if state == "":
                if line.strip() == "":
                    continue
                if line.strip().startswith("** "):
                    state = line[3:].lower()
                    acc = []
            else:
                if line.strip().startswith("** "):
                    handleState(result, acc, state)
                    state = line[3:].lower()
                    acc = []
                else:
                    acc.append(line)
        handleState(result, acc, state)
        if result.id == None:
            return None
        else:
            return result
    
    def __init__(self, id, title, assignee, status, comments):
        self.id = id
        self.title = title
        self.assignee = assignee
        self.status = status
        self.comments = comments
        
    def link(self):
        return "/edit-bug/" + str(self.id)
        
    def addComment(self, newComment):
        self.comments.append(newComment)
        
    def containsAny(self, words):
        content = self.serialize().lower()
        words = [w.lower() for w in words]
        for w in words:
            if w in content:
                return True
        return False
        
    def serialize(self):
        content = []
        content.append("** ID")
        content.append(str(self.id))
        content.append("** TITLE")
        content.append(self.title)
        content.append("** ASSIGNEE")
        content.append(self.assignee)
        content.append("** STATUS")
        content.append(self.status)
        for comment in self.comments:
            content.append("** COMMENT %s %s" % (comment.author, comment.formatDate()))
            content.append(comment.content)
        return "\n".join(content)

class Container:
    pass

def makePage(text, link, active):
    result = Container()
    result.text = text
    result.link = link
    if active == link:
        result.cls = "active"
    else:
        result.cls = ""
    return result

def getPages(active):
    return [makePage("Home", "/", active),
            makePage("Bugs", "/bugs", active),
            makePage("Documentation", "/documentation", active),
            makePage("Contact", "/contact", active)]
    
class IndexHandler:
    def GET(self):
        return render.main(render.index(), getPages("/"))

class DocumentationHandler:
    def GET(self):
        return render.main(render.documentation(), getPages("/documentation"))

class ContactHandler:
    def GET(self):
        return render.main(render.contact(), getPages("/contact"))
        
def readFile(fn):
    f = open(fn)
    content = f.read()
    f.close()
    return content
    
def writeFile(fn, content):
    f = open(fn, 'w')
    f.write(content)
    f.close()
    
def listBugs():
    result = []
    for filename in glob.glob("bugs/*"):
        candidate = Bug.deserialize(readFile(filename))
        if candidate:
            result.append(candidate)
    return result
    
def findBug(bugId):
    for filename in glob.glob("bugs/*"):
        candidate = Bug.deserialize(readFile(filename))
        if candidate and bugId == candidate.id:
            return candidate
    return None
    
def writeBug(bugId, bug):
    writeFile("bugs/" + bugId, bug.serialize())
    
config = None
def getConfig():
    global config
    if config == None:
        if len(glob.glob("config.json")) > 0:
            config = json.loads(readFile("config.json"))
        else:
            config = { "users": [],
                       "statuses": [ "New",
                                     "In Progress",
                                     "Fixed",
                                     "Closed" ],
                       "closedStatus": "Closed" }
    return config
    
currentUser = None
def getCurrentUser():
    global currentUser
    if currentUser == None:
        proc = subprocess.Popen("git config --global --get user.email", stdout=subprocess.PIPE)
        proc.wait()
        currentUser = proc.stdout.read().strip()
    return currentUser
    
def makeBug():
    suffix = getSuffixesDict()[getCurrentUser()]
    bugIds = [int(bug.id[:-len(suffix)]) for bug in listBugs() if bug.id.endswith(suffix)]
    if len(bugIds) > 0:
        id = max(bugIds) + 1
    else:
        id = 1
    result = Bug(str(id) + suffix, '', 'Nobody', getConfig()["newStatus"], [])
    return result

class BugsHandler:
    def GET(self):
        bugs = listBugs()
        i = web.input()
        c = ""
        q = ""
        a = ""
        if 'q' in i:
            words = i.q.split(' ')
            bugs = [b for b in bugs if b.containsAny(words)]
            q = i.q
        abugs = []
        cbugs = []
        if 'c' in i:
            c = "checked"
        if 'a' in i:
            a = "checked"
        if 'a' not in i and 'c' not in i:
            a = "checked"
        closedStatus = getConfig()["closedStatus"].lower()
        if a == "checked":
            abugs = [b for b in bugs if b.status.lower() != closedStatus]
        if c == "checked":
            cbugs = [b for b in bugs if b.status.lower() == closedStatus]
        return render.main(render.bugs(abugs + cbugs, q, a, c), getPages("/bugs"))
        
def makeOption(name, current):
    result = Container()
    result.name = name
    result.value = name
    if name == current:
        result.selected = "selected"
    else:
        result.selected = ""
    return result
    
class EditBugHandler:
    def GET(self, bugId):
        bug = findBug(bugId)
        if bug == None:
            flashMessage('Bug not found')
            raise web.seeother('/bugs')
        session.bug = bug.deserialize(bug.serialize())
        raise web.seeother('/bug-editor')
            
class NewBugHandler:
    def GET(self):
        session.bug = makeBug()
        raise web.seeother('/bug-editor')
        
def getSortedUsers(includeNobody):
    users = [b.assignee for b in listBugs()]
    users.append(getCurrentUser())
    if includeNobody:
        users.append('Nobody')
    users += getConfig()["users"]
    users = set(users)
    if not includeNobody:
        users = users.difference(set(["Nobody"]))
    users = list(users)
    users.sort()
    return users   
    
def letterify(n):
    if n < 25:
        return chr(ord('A') + n)
    else:
        return letterify(n / 26) + letterify(n % 26)
    
def getSuffixesDict():
    users = getSortedUsers(False)
    suffixes = {}
    for x in range(len(users)):
        suffixes[users[x]] = letterify(x)
    return suffixes
            
class BugEditorHandler:
    def GET(self):
        if 'bug' not in session:
            raise web.seeother('/bugs')
        bug = session.bug
        statuses = [makeOption(s, bug.status) for s in getConfig()["statuses"]]
        assignees = []
        users = getSortedUsers(True)
        for user in users:
            assignees.append(makeOption(user, bug.assignee))
        return render.main(render.editBug(bug, statuses, assignees), getPages("/bugs"))

class SaveBugHandler:
    def POST(self):
        i = web.input()
        bugId = i.id
        if 'bug' not in session:
            bug = findBug(bugId)
            if bug == None:
                flashMessage('Bug not found')
                raise web.seeother('/bugs')
        else:
            bug = session.bug
        bug.title = i.title
        bug.status = i.status
        bug.assignee = i.assignee
        if i.title.strip() == "":
            flashMessage("Title cannot be empty")
            raise web.seeother('/bug-editor')
        if i.comment.strip() != "":
            bug.comments.append(Comment(time.gmtime(), getCurrentUser(), i.comment.strip()))
        writeBug(bugId, bug)
        flashMessage("Bug '%s' (%s) saved." % (i.title, i.id))
        raise web.seeother('/bugs')
        
if __name__ == "__main__":
    os.startfile("http://localhost:8080/")
    app.run()
