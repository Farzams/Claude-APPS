cmake_minimum_required(VERSION 3.18)
project(djvubridge CXX)

# DjVuLibre's sources are fetched by android/tools/fetch_djvu.sh into ./djvulibre (not stored in git).
set(DJVU ${CMAKE_CURRENT_SOURCE_DIR}/djvulibre)
set(NAMES Arrays BSByteStream BSEncodeByteStream ByteStream DataPool DjVmDir DjVmDir0 DjVmDoc DjVmNav DjVuAnno DjVuDocEditor
    DjVuDocument DjVuDumpHelper DjVuErrorList DjVuFile DjVuFileCache DjVuGlobal DjVuGlobalMemory DjVuImage DjVuInfo DjVuMessage
    DjVuMessageLite DjVuNavDir DjVuPalette DjVuPort DjVuText DjVuToPS GBitmap GContainer GException GIFFManager GMapAreas GOS
    GPixmap GRect GScaler GSmartPointer GString GThreads GURL GUnicode IFFByteStream IW44EncodeCodec IW44Image JB2EncodeCodec
    JB2Image JPEGDecoder MMRDecoder MMX UnicodeByteStream XMLParser XMLTags ZPCodec atomic ddjvuapi debug miniexp)
set(SRCS djvu_bridge.cpp)
foreach(n ${NAMES})
  list(APPEND SRCS ${DJVU}/libdjvu/${n}.cpp)
endforeach()

if(ANDROID)
  add_library(djvubridge SHARED ${SRCS} djvu_jni.cpp)
  target_link_libraries(djvubridge log)
else()
  add_library(djvubridge STATIC ${SRCS})            # host test build
endif()
target_include_directories(djvubridge PRIVATE ${CMAKE_CURRENT_SOURCE_DIR} ${DJVU} ${DJVU}/libdjvu)
target_compile_definitions(djvubridge PRIVATE HAVE_CONFIG_H DIR_DATADIR="/nonexistent")
set_target_properties(djvubridge PROPERTIES CXX_STANDARD 11 CXX_STANDARD_REQUIRED ON CXX_EXTENSIONS ON)
target_compile_options(djvubridge PRIVATE -w -fexceptions -frtti -O2 "SHELL:-include errno.h" "SHELL:-include string.h" "SHELL:-include stdlib.h" "SHELL:-include stdio.h" "SHELL:-include unistd.h")
if(NOT ANDROID)
  find_package(Threads REQUIRED)
  add_executable(djvutest test_main.cpp)
  target_link_libraries(djvutest djvubridge Threads::Threads)
  target_include_directories(djvutest PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
endif()
