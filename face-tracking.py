#!/usr/bin/python

from OpenGL.GLUT import *
from OpenGL.GLU  import *
from OpenGL.GL   import *
from opencv      import *
from math        import *
from random      import *
import sys

class FaceTracking:
    def __init__(self):
        self.init_glut()
        self.init_cv()
        self.init_tracker()
        self.init_scene()

    def init_glut(self):
        glutInit(sys.argv)
        glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
        glutInitWindowSize(640, 480)
        glutCreateWindow('Face Tracking')

        glClearColor(0.0, 0.0, 0.0, 1.0)
        glShadeModel(GL_SMOOTH)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_TEXTURE_2D)
        glutReshapeFunc(self.on_reshape)
        glutDisplayFunc(self.on_display)
        glutKeyboardFunc(self.on_key)
        glutIdleFunc(self.on_idle)

        self.frame_texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.frame_texture);
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP)
        glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_DECAL)

        self.scene = glGenLists(1)

    def init_cv(self):
        self.cascade  = cvLoadHaarClassifierCascade('/usr/share/opencv/haarcascades/haarcascade_frontalface_alt2.xml', cvSize(1, 1))
        self.storage  = cvCreateMemStorage(0)
        self.capture  = cvCaptureFromCAM(0)
        self.frame    = cvQueryFrame(self.capture)
        self.gray     = cvCreateImage(cvSize(self.frame.width, self.frame.height), 8, 1)
        self.prev     = cvCreateImage(cvSize(self.frame.width, self.frame.height), 8, 1)
        self.eigs     = cvCreateImage(CvSize(self.frame.width, self.frame.height), 32, 1)
        self.temp     = cvCreateImage(CvSize(self.frame.width, self.frame.height), 32, 1)
        self.pyr_a    = cvCreateImage(CvSize(self.frame.width, self.frame.height), 32, 1)
        self.pyr_b    = cvCreateImage(CvSize(self.frame.width, self.frame.height), 32, 1)
        self.features = None

    def init_tracker(self):
        self.state = 'choose_face'
        self.flags, self.x, self.y, self.spread, self.distance = 0, 0, 0, 0, 1
        self.show_frame = False
        self.face_candidate = None

    def init_scene(self):
        def generate_target():
            x, y, z = uniform(-7.5, 7.5), uniform(-4.5, 4.5), uniform(-15, 5)
            return (x, y, z, (z+15.0)/15.0, 0, 0)
        targets = [generate_target() for x in range(0, 40)]

        glNewList(self.scene, GL_COMPILE)

        glBegin(GL_LINES)
        for z in range(-15, 1):
            glColor3f(1.0+(z/10.0), 1.0+(z/15.0), 1.0+(z/15.0))
            glVertex3f(-8, -5, z); glVertex3f(-8,  5, z)
            glVertex3f(-8, -5, z); glVertex3f( 8, -5, z)
            glVertex3f( 8,  5, z); glVertex3f(-8,  5, z)
            glVertex3f( 8,  5, z); glVertex3f( 8, -5, z)
        for x in range(-8, 9):
            glColor3f(1.0, 1.0, 1.0); glVertex3f(x, -5, 0); glColor3f(0.0, 0.0, 0.0); glVertex3f(x, -5, -15)
            glColor3f(1.0, 1.0, 1.0); glVertex3f(x,  5, 0); glColor3f(0.0, 0.0, 0.0); glVertex3f(x,  5, -15)
        for y in range(-5, 6):
            glColor3f(1.0, 1.0, 1.0); glVertex3f(-8, y, 0); glColor3f(0.0, 0.0, 0.0); glVertex3f(-8, y, -15)
            glColor3f(1.0, 1.0, 1.0); glVertex3f( 8, y, 0); glColor3f(0.0, 0.0, 0.0); glVertex3f( 8, y, -15)
        for (x, y, z, r, g, b) in targets:
            glColor3f(1.0, 1.0, 1.0); glVertex3f(x, y, z-0.02); glColor3f(0.0, 0.0, 0.0); glVertex3f(x, y, -15)
        glEnd()

        glBegin(GL_QUADS)
        for (x, y, z, r, g, b) in targets:
            glColor3f(r, g, b); glVertex3f(0.5+x, 0.5+y, z); glVertex3f(-0.5+x, 0.5+y, z); glVertex3f(-0.5+x, -0.5+y, z); glVertex3f(0.5+x, -0.5+y, z)
        glEnd()

        glEndList()

    def on_reshape(self, w, h):
        glViewport(0, 0, w, h)
        self.width  = w
        self.height = h

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45.0, w/float(h), 0.1, 100.0)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

    def on_display(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        glTranslatef(0.0, 0.0, -5.0)
        gluLookAt(self.x, self.y, abs(self.distance*6), 0.0, 0.0, 0.0, 0.0, 1.0, 0.0)
        glCallList(self.scene);

        if self.show_frame:
            glMatrixMode(GL_PROJECTION)
            glPushMatrix()
            glLoadIdentity()
            glOrtho(0, self.width, self.height, 0, -1, 1)

            glMatrixMode(GL_MODELVIEW)
            glPushMatrix()
            glLoadIdentity()

            glBindTexture(GL_TEXTURE_2D, self.frame_texture)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB8, 640, 480, 0, GL_BGR, GL_UNSIGNED_BYTE, self.frame.data_as_string());
            glBegin(GL_POLYGON);
            glTexCoord2f(1.0, 0.0); glVertex2f(  0.0,   0.0)
            glTexCoord2f(0.0, 0.0); glVertex2f(640.0,   0.0)
            glTexCoord2f(0.0, 1.0); glVertex2f(640.0, 480.0)
            glTexCoord2f(1.0, 1.0); glVertex2f(  0.0, 480.0)
            glEnd();
            glBindTexture(GL_TEXTURE_2D, 0)

            glMatrixMode(GL_PROJECTION)
            glPopMatrix()

            glMatrixMode(GL_MODELVIEW)
            glPopMatrix()

        glutSwapBuffers()

    def on_key(self, k, *args):
        if k in ['q', chr(27)]:
            sys.exit(0)
        elif k in ['m', chr(10), chr(13)]:
            self.state = 'mark_face'
        elif k in ['c']:
            self.state = 'choose_face'
        elif k in ['s']:
            self.init_scene()
        elif k in ['f']:
            self.show_frame = not self.show_frame

    def on_idle(self):
        self.frame = cvQueryFrame(self.capture)

        cvCvtColor(self.frame, self.gray, CV_BGR2GRAY)
        cvEqualizeHist(self.gray, self.gray)
        cvClearMemStorage(self.storage)

        if self.state == 'choose_face':
            self.state_choose_face()
        elif self.state == 'mark_face':
            self.state_mark_face()
        elif self.state == 'track_face':
            self.state_track_face()

        cvCopy(self.gray, self.prev)
        self.pyr_a, self.pyr_b = self.pyr_b, self.pyr_a

        glutPostRedisplay()

    def state_choose_face(self):
        self.face_candidate = None

        for face in cvHaarDetectObjects(self.gray, self.cascade, self.storage, 1.1, 2, CV_HAAR_DO_CANNY_PRUNING, cvSize(100, 100)):
            conservative = CvRect(face.x+30, face.y+30, face.width-60, face.height-60)

            if not self.face_candidate or conservative.height > self.face_candidate.height:
                self.face_candidate = conservative

            cvRectangle(self.frame,
                        CvPoint(conservative.x,                    conservative.y),
                        CvPoint(conservative.x+conservative.width, conservative.y+conservative.height),
                        CV_RGB(255, 0, 0), 3, 8, 0)

        if self.face_candidate:
            cvRectangle(self.frame, CvPoint(self.face_candidate.x, self.face_candidate.y), CvPoint(self.face_candidate.x+self.face_candidate.width, self.face_candidate.y+self.face_candidate.height), CV_RGB(0, 255, 0), 3, 8, 0)

    def state_mark_face(self):
        if not self.face_candidate:
            return

        for image in [self.gray, self.eigs, self.temp]:
            cvSetImageROI(image, self.face_candidate)

        self.features = [x for x in cvGoodFeaturesToTrack(self.gray, self.eigs, self.temp, None, 100, 0.05, 6.0, use_harris=False)]
        min_x, max_x  = 1000, 0
        for f in self.features:
            f.x, f.y = f.x + self.face_candidate.x, f.y + self.face_candidate.y
            min_x, max_x = min(min_x, f.x), max(max_x, f.x)

        print "found features:", len(self.features)

        for image in [self.gray, self.eigs, self.temp]:
            cvResetImageROI(image)

        anglePerPixel = (3.14159 / 4.5) / 480.0
        angle         = (self.face_candidate.width + 60) * anglePerPixel

        self.distance = (0.12/2.0) / tan(angle/2.0)
        self.x        = (320 - (self.face_candidate.x + (self.face_candidate.width  / 2.0))) / 160.0 * self.distance
        self.y        = (240 - (self.face_candidate.y + (self.face_candidate.height / 2.0))) / 120.0 * self.distance
        self.spread   = max_x - min_x
        self.flags    = 0
        self.state    = 'track_face'

    def state_track_face(self):
        features, status = cvCalcOpticalFlowPyrLK(self.prev, self.gray, self.pyr_a, self.pyr_b, self.features, None, None, CvSize(50, 50), 3, None, None, cvTermCriteria(CV_TERMCRIT_ITER|CV_TERMCRIT_EPS, 10, 0.03), self.flags)
        features = [x for x in features]
        dx, dy, min_x, max_x, = 0, 0, 1000, 0
        for i in range(0, len(features)):
            if ord(status[i]) == 0:
                features[i] = None
            else:
                dx = dx + (self.features[i].x - features[i].x)
                dy = dy + (self.features[i].y - features[i].y)
                min_x, max_x = min(min_x, features[i].x), max(max_x, features[i].x)
                cvCircle(self.frame, cvPoint(int(features[i].x), int(features[i].y)), 3, CV_RGB(0, 0, 255), 1)

        features = [x for x in features if x]
        if len(features) > 0:
            dx, dy = dx / len(features), dy / len(features)

        spread = max_x - min_x

        self.features = features
        self.distance  = self.distance * (self.spread / spread)
        self.x         = self.x + (dx / 160.0 * self.distance)
        self.y         = self.y + (dy / 120.0 * self.distance)
        self.flags     = CV_LKFLOW_PYR_A_READY
        self.spread    = spread

        if len(self.features) < 20:
            self.state = 'mark_face'

    def main(self):
        glutMainLoop()

if __name__ == '__main__':
    FaceTracking().main()