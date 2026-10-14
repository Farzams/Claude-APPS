/* Host-only check: renders every page of a DjVu file to a PPM. Not part of the Android build. */
#include "djvu_bridge.h"
#include <cstdio>
#include <vector>
int main(int argc, char** argv) {
    void* h = djvu_open(argv[1]);
    if (!h) { printf("open failed\n"); return 1; }
    int n = djvu_page_count(h);
    printf("pages %d\n", n);
    for (int i = 0; i < n; i++) {
        int info[3];
        if (djvu_page_info(h, i, info)) { printf("info failed\n"); return 2; }
        printf("page %d: %dx%d @%ddpi\n", i, info[0], info[1], info[2]);
        int w = info[0] / 2, hh = info[1] / 2;
        std::vector<unsigned char> rgb((size_t)w * hh * 3);
        if (djvu_render(h, i, w, hh, rgb.data())) { printf("render failed\n"); return 3; }
        long dark = 0;
        for (size_t k = 0; k < rgb.size(); k += 3) if (rgb[k] < 128) dark++;
        printf("  dark pixels: %ld\n", dark);
        char name[64]; snprintf(name, sizeof name, "%s_%d.ppm", argv[2], i);
        FILE* f = fopen(name, "wb"); fprintf(f, "P6\n%d %d\n255\n", w, hh); fwrite(rgb.data(), 1, rgb.size(), f); fclose(f);
    }
    djvu_close(h);
    return 0;
}
