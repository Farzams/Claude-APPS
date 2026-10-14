#include "djvu_bridge.h"
#include <libdjvu/ddjvuapi.h>
#include <cstdlib>

struct Doc {
    ddjvu_context_t* ctx;
    ddjvu_document_t* doc;
};

static void pump(ddjvu_context_t* ctx) {
    ddjvu_message_wait(ctx);
    while (ddjvu_message_peek(ctx)) ddjvu_message_pop(ctx);
}

extern "C" void* djvu_open(const char* path) {
    ddjvu_context_t* ctx = ddjvu_context_create("pdfora");
    if (!ctx) return nullptr;
    ddjvu_document_t* d = ddjvu_document_create_by_filename(ctx, path, 0);
    if (!d) { ddjvu_context_release(ctx); return nullptr; }
    while (!ddjvu_document_decoding_done(d)) pump(ctx);
    if (ddjvu_document_decoding_error(d)) {
        ddjvu_document_release(d);
        ddjvu_context_release(ctx);
        return nullptr;
    }
    Doc* r = new Doc{ctx, d};
    return r;
}

extern "C" int djvu_page_count(void* h) {
    return h ? ddjvu_document_get_pagenum(static_cast<Doc*>(h)->doc) : 0;
}

static ddjvu_page_t* load_page(Doc* d, int page) {
    ddjvu_page_t* p = ddjvu_page_create_by_pageno(d->doc, page);
    if (!p) return nullptr;
    while (!ddjvu_page_decoding_done(p)) pump(d->ctx);
    if (ddjvu_page_decoding_error(p)) { ddjvu_page_release(p); return nullptr; }
    return p;
}

extern "C" int djvu_page_info(void* h, int page, int* out) {
    Doc* d = static_cast<Doc*>(h);
    if (!d) return -1;
    ddjvu_page_t* p = load_page(d, page);
    if (!p) return -2;
    out[0] = ddjvu_page_get_width(p);
    out[1] = ddjvu_page_get_height(p);
    out[2] = ddjvu_page_get_resolution(p);
    ddjvu_page_release(p);
    return 0;
}

extern "C" int djvu_render(void* h, int page, int w, int hh, unsigned char* rgb) {
    Doc* d = static_cast<Doc*>(h);
    if (!d) return -1;
    ddjvu_page_t* p = load_page(d, page);
    if (!p) return -2;
    ddjvu_rect_t rect = {0, 0, (unsigned int)w, (unsigned int)hh};
    ddjvu_format_t* fmt = ddjvu_format_create(DDJVU_FORMAT_RGB24, 0, nullptr);
    ddjvu_format_set_row_order(fmt, 1);
    int ok = ddjvu_page_render(p, DDJVU_RENDER_COLOR, &rect, &rect, fmt, (unsigned long)w * 3, reinterpret_cast<char*>(rgb));
    ddjvu_format_release(fmt);
    ddjvu_page_release(p);
    return ok ? 0 : -3;
}

extern "C" void djvu_close(void* h) {
    Doc* d = static_cast<Doc*>(h);
    if (!d) return;
    ddjvu_document_release(d->doc);
    ddjvu_context_release(d->ctx);
    delete d;
}
