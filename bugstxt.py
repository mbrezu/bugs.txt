
import web
import os
import time

web.config.debug = True

urls = (
    '/', 'index',
    '/documentation', 'documentation',
    '/bugs', 'bugs',
    '/edit-bug/(.*)', 'editBug',
    '/contact', 'contact',
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
    if 'flashCounter' not in session:
        session.flashCounter = 0
        session.flashMessage = ''
    result = handler()
    session.flashCounter -= 1
    if session.flashCounter <= 0:
        session.flashCounter = 0
        session.flashMessage = ''
    return result
    
app.add_processor(flashMessageProcessor)

def flashMessage(message):
    session.flashCounter = 1
    session.flashMessage = message

render = web.template.render("templates/",
                             globals = {'session': session})

class comment:
    def __init__(self, date, author, content):
        self.date = date
        self.author = author
        self.content = content
        
timeFormat = '%Y-%m-%d_%H:%M:%S'
        
class bug:
    # @staticmethod
    # def deserialize(text):
    #     lines = text.split("\n")
    #     id = 0
    #     title = ""
    #     assignee = ""
    #     status = ""
    #     comments = []
    #     state = 0
    #     acc = []
    #     def handleAcc():
    #         if len(acc) == 0:
    #             return
    #         firstLine = None
    #         lastLine = None
    #         index = 0
    #         for line in acc:
    #             if firstLine == None and line.strip() != null:
    #                 firstLine = index
    #             lastLine = index
    #             index += 1
    #         lastLine += 1
    #         acc = acc[firstLine:lastLine]
    #         content = "\n".join(acc)
    #         if state == "id":
    #             id = int(acc)
    #         elif state == "title":
    #             title = acc
    #         elif state == "assignee":
    #             assignee = acc
    #         elif state == "status":
    #             status = acc
    #         elif state.startswith("comment"):
    #             stateContent = state.split(' ')
    #             comments.append(comment(time.strptime(timeFormat, stateContent[2]),
    #                                     stateContent[1], 
    #                                     acc))
    #     for line in lines:
    #         if state == 0:
    #             if line.strip() == "":
    #                 continue
    #             if line.strip().startswith("** "):
    #                 state = line[3:].lower()
    #                 acc = []
    #         else:
    #             if line.strip().startswith("** "):
    #                 handleAcc()
    #                 state = line[3:].lower()
    #                 acc = []
    #     handleAcc()           
    #     if id == 0:
    #         return None
    #     else:
    #         return bug(id, title, assignee, status, comments)
    
    def __init__(self, id, title, assignee, status, comments):
        self.id = id
        self.title = title
        self.assignee = assignee
        self.status = status
        self.comments = comments
        self.link = "/edit-bug/" + str(id)
        
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
            content.append("** COMMENT %s %s" % (comment.author, time.strftime(comment.date, timeFormat)))
            content.append(comment)
        return "\n".join(content)

class container:
    pass

def makePage(text, link, active):
    result = container()
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
    
class index:
    def GET(self):
        return render.main(render.index(), getPages("/"))

class documentation:
    def GET(self):
        web.debug("shit")
        return render.main(render.documentation(), getPages("/documentation"))

class contact:
    def GET(self):
        return render.main(render.contact(), getPages("/contact"))
        
def newBug(id, title):
    return bug(id, title, "mbrezu@gmail.com", "New", [])
    
theBugs = []       
theBugs.append(newBug(1, "Some bug"))
theBugs.append(newBug(2, "Other bug"))
theBugs.append(newBug(3, "Yet another"))
theBugs.append(newBug(4, "Guess what"))

class bugs:
    def GET(self):
        web.debug(repr(session.keys()))
        return render.main(render.bugs(theBugs), getPages("/bugs"))
        
class editBug:
    def GET(self, bugId):
        bugId = int(bugId)
        bug = None
        if bug == None:
            flashMessage('Bug not found')
            raise web.seeother('/bugs')

if __name__ == "__main__":
    os.startfile("http://localhost:8080/")
    app.run()
