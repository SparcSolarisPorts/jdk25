#define _POSIX_C_SOURCE 200809L
#include <jni.h>
#include <errno.h>
#include <time.h>

static void pause_in_native(void) {
    struct timespec delay = {0, 100000};
    while (nanosleep(&delay, &delay) != 0 && errno == EINTR) {}
}
JNIEXPORT jobject JNICALL Java_NativeReturnGcSmoke_echo(JNIEnv* env, jclass klass, jobject value) {
    (void)env; (void)klass;
    pause_in_native();
    return value;
}
JNIEXPORT jlong JNICALL Java_NativeReturnGcSmoke_echoLong(JNIEnv* env, jclass klass, jlong value) {
    (void)env; (void)klass;
    pause_in_native();
    return value;
}
