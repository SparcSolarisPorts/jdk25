/*
 * Copyright (c) 2023, 2024, Oracle and/or its affiliates. All rights reserved.
 * DO NOT ALTER OR REMOVE COPYRIGHT NOTICES OR THIS FILE HEADER.
 *
 * This code is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License version 2 only, as
 * published by the Free Software Foundation.
 *
 * This code is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 * FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
 * version 2 for more details (a copy is included in the LICENSE file that
 * accompanied this code).
 *
 * You should have received a copy of the GNU General Public License version
 * 2 along with this work; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA.
 *
 * Please contact Oracle, 500 Oracle Parkway, Redwood Shores, CA 94065 USA
 * or visit www.oracle.com if you need additional information or have any
 * questions.
 */

#include <stdio.h>
#include "jni.h"

#include "export.h"

/*
 * Call a function with the given function pointer.
 */
EXPORT void call(void *(*f)(void)) {
    (*f)();
}

/*
 * Java -> JNI -> Java leaves a native frame below task.run(), pinning the
 * virtual thread just as the FFM downcall/upcall does. Keep the existing call
 * symbol for ports using FFM. Let JNI exceptions propagate to runPinned.
 */
JNIEXPORT void JNICALL
Java_jdk_test_lib_thread_VThreadPinner_invokePinned(JNIEnv* env, jclass klass,
                                                  jobject task) {
    jclass task_class = (*env)->GetObjectClass(env, task);
    if (task_class == NULL) return;
    jmethodID run = (*env)->GetMethodID(env, task_class, "run", "()V");
    if (run != NULL) {
        (*env)->CallVoidMethod(env, task, run);
    }
    (*env)->DeleteLocalRef(env, task_class);
}
