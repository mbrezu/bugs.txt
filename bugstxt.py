
import web
import os
import time
import glob
import subprocess

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
        result.id = int(content)
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
    writeFile("bugs/%d" % (bugId,), bug.serialize())
    
def getCurrentUser():
    proc = subprocess.Popen("git config --global --get user.email", stdout=subprocess.PIPE)
    proc.wait()
    return proc.stdout.read().strip()
    
def makeBug():
    bugIds = [bug.id for bug in listBugs()]
    if len(bugIds) > 0:
        id = max(bugIds) + 1
    else:
        id = 1
    result = Bug(id, '', 'Nobody', 'New', [])
    return result

class BugsHandler:
    def GET(self):
        return render.main(render.bugs(listBugs()), getPages("/bugs"))
        
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
        bugId = int(bugId)
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
            
class BugEditorHandler:
    def GET(self):
        if 'bug' not in session:
            raise web.seeother('/bugs')
        bug = session.bug
        statuses = [makeOption('New', bug.status),
                    makeOption('In Progress', bug.status),
                    makeOption('Fixed', bug.status),
                    makeOption('Closed', bug.status)]
        assignees = [makeOption('Nobody', bug.assignee)]
        users = set([b.assignee for b in listBugs()]).union(set([getCurrentUser()]))
        for user in users:
            assignees.append(makeOption(user, bug.assignee))
        return render.main(render.editBug(bug, statuses, assignees), getPages("/bugs"))

class SaveBugHandler:
    def POST(self):
        i = web.input()
        bugId = int(i.id)
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
