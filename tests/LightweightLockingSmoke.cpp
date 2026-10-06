#include <jni.h>

// One Java receiver is shared by all workers; the synchronized native wrapper
// must serialize both functions without a C++ mutex.
static jlong counter = 0;
extern "C" JNIEXPORT jlong JNICALL
Java_LightweightLockingSmoke_nativeIncrement(JNIEnv*, jobject) {
  return ++counter;
}
extern "C" JNIEXPORT jlong JNICALL
Java_LightweightLockingSmoke_nativeCount(JNIEnv*, jobject) {
  return counter;
}
