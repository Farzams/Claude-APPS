#ifndef DJVU_BRIDGE_H
#define DJVU_BRIDGE_H
#ifdef __cplusplus
extern "C" {
#endif
/* A small C interface over DjVuLibre's ddjvuapi: open, count pages, read page size, render to RGB. */
void* djvu_open(const char* path);
int djvu_page_count(void* h);
/* out[0]=width px, out[1]=height px, out[2]=dpi (at the page's own resolution). Returns 0 on success. */
int djvu_page_info(void* h, int page, int* out);
/* Renders the page scaled to w x h into rgb (w*h*3 bytes, top row first). Returns 0 on success. */
int djvu_render(void* h, int page, int w, int h2, unsigned char* rgb);
void djvu_close(void* h);
#ifdef __cplusplus
}
#endif
#endif
