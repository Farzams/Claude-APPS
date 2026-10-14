#include <jni.h>
#include <vector>
#include "djvu_bridge.h"

extern "C" {

JNIEXPORT jlong JNICALL Java_app_pdftoolkit_djvu_DjvuNative_open(JNIEnv* env, jclass, jstring path) {
    const char* p = env->GetStringUTFChars(path, nullptr);
    void* h = djvu_open(p);
    env->ReleaseStringUTFChars(path, p);
    return reinterpret_cast<jlong>(h);
}

JNIEXPORT jint JNICALL Java_app_pdftoolkit_djvu_DjvuNative_pageCount(JNIEnv*, jclass, jlong h) {
    return djvu_page_count(reinterpret_cast<void*>(h));
}

JNIEXPORT jint JNICALL Java_app_pdftoolkit_djvu_DjvuNative_pageInfo(JNIEnv* env, jclass, jlong h, jint page, jintArray out) {
    int v[3] = {0, 0, 0};
    int r = djvu_page_info(reinterpret_cast<void*>(h), page, v);
    if (r == 0) env->SetIntArrayRegion(out, 0, 3, v);
    return r;
}

/* Fills argb with opaque pixels (0xFFRRGGBB), w*h entries, top row first. */
JNIEXPORT jint JNICALL Java_app_pdftoolkit_djvu_DjvuNative_render(JNIEnv* env, jclass, jlong h, jint page, jint w, jint hh, jintArray argb) {
    std::vector<unsigned char> rgb((size_t)w * hh * 3);
    int r = djvu_render(reinterpret_cast<void*>(h), page, w, hh, rgb.data());
    if (r != 0) return r;
    std::vector<jint> px((size_t)w * hh);
    for (size_t i = 0; i < px.size(); i++) {
        px[i] = (jint)(0xFF000000u | (rgb[i * 3] << 16) | (rgb[i * 3 + 1] << 8) | rgb[i * 3 + 2]);
    }
    env->SetIntArrayRegion(argb, 0, (jsize)px.size(), px.data());
    return 0;
}

JNIEXPORT void JNICALL Java_app_pdftoolkit_djvu_DjvuNative_close(JNIEnv*, jclass, jlong h) {
    djvu_close(reinterpret_cast<void*>(h));
}

}
