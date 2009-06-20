#include "cv.h"
#include "highgui.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <math.h>
#include <float.h>
#include <limits.h>
#include <time.h>
#include <ctype.h>

static CvMemStorage* storage = 0;
static CvHaarClassifierCascade* cascade = 0;
static IplImage* gray = 0;
static IplImage* small_img = 0;

static double scale = 1.3;

void detect_and_draw( IplImage* image );

const char* cascade_name = "/usr/share/opencv/haarcascades/haarcascade_frontalface_alt2.xml";

int main( int argc, char** argv ) {
    CvCapture* capture = 0;
    IplImage *frame, *frame_copy = 0;

    cascade = (CvHaarClassifierCascade*) cvLoad(cascade_name, 0, 0, 0);
    storage = cvCreateMemStorage(0);
    capture = cvCaptureFromCAM(0);

    cvNamedWindow("result", 1);

    while (1) {
        if (!cvGrabFrame(capture))
            break;

        frame = cvRetrieveFrame(capture);
        if (!frame)
            break;

        if (!gray)
            gray = cvCreateImage(cvSize(frame->width, frame->height), 8, 1);

        if (!small_img)
            small_img = cvCreateImage(cvSize(cvRound(frame->width/scale), cvRound(frame->height/scale)), 8, 1);

        detect_and_draw(frame);

        if(cvWaitKey(10) >= 0)
            break;
    }

    cvReleaseImage(&gray);
    cvReleaseImage(&small_img);
    cvReleaseImage(&frame);
    cvReleaseCapture(&capture);
    cvDestroyWindow("result");

    return 0;
}

void detect_and_draw(IplImage* img) {
    static CvScalar colors[] = { {{0,0,255}},
                                 {{0,128,255}},
                                 {{0,255,255}},
                                 {{0,255,0}},
                                 {{255,128,0}},
                                 {{255,255,0}},
                                 {{255,0,0}},
                                 {{255,0,255}} };

    int i;

    cvCvtColor(img, gray, CV_BGR2GRAY);
    cvResize(gray, small_img, CV_INTER_LINEAR);
    cvEqualizeHist(small_img, small_img);
    cvClearMemStorage(storage);

    double t = (double)cvGetTickCount();
    CvSeq* faces = cvHaarDetectObjects(small_img, cascade, storage, 1.1, 2, 0, cvSize(30, 30));
    t = (double)cvGetTickCount() - t;
    printf( "detection time = %gms\n", t/((double)cvGetTickFrequency()*1000.) );

    for (i = 0; i < (faces ? faces->total : 0); i++) {
        CvRect* r = (CvRect*)cvGetSeqElem(faces, i);
        CvPoint center;
        int radius;
        center.x = cvRound((r->x + r->width*0.5)*scale);
        center.y = cvRound((r->y + r->height*0.5)*scale);
        radius = cvRound((r->width + r->height)*0.25*scale);
        cvCircle(img, center, radius, colors[i%8], 3, 8, 0);
    }

    cvShowImage("result", img);
}
