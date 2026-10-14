/* Minimal configuration for building DjVuLibre with the Android NDK (and for testing on Linux). */
#ifndef CONFIG_H
#define CONFIG_H
#define DJVULIBRE_VERSION "3.5.28"
#define HAVE_BOOL 1
#define HAVE_DIRENT_H 1
#define HAVE_EXCEPTIONS 1
#define HAVE_FSEEKO 1
#define HAVE_INTEL_ATOMIC_BUILTINS 1
#define HAVE_INTTYPES_H 1
#define HAVE_ISWSPACE 1
#define HAVE_LONG_LONG_INT 1
#define HAVE_MBSTATE_T 1
#define HAVE_MEMBER_TEMPLATES 1
#define HAVE_MEMORY_H 1
#define HAVE_MKSTEMP 1
#define HAVE_MMAP 1
#define HAVE_NAMESPACES 1
#define HAVE_PTHREAD 1
#define HAVE_SCHED_H 1
#define HAVE_SCHED_YIELD 1
#define HAVE_SETENV 1
#define HAVE_STDINCLUDES 1
#define HAVE_STDINT_H 1
#define HAVE_STDLIB_H 1
#define HAVE_STRERROR 1
#define HAVE_STRFTIME 1
#define HAVE_STRINGS_H 1
#define HAVE_STRING_H 1
#define HAVE_SYS_MMAN_H 1
#define HAVE_SYS_PARAM_H 1
#define HAVE_SYS_STAT_H 1
#define HAVE_SYS_TYPES_H 1
#define HAVE_TYPENAME 1
#define HAVE_UNISTD_H 1
#define HAVE_VSNPRINTF 1
#define HAVE_WCHAR_H 1
#define HAVE_WCHAR_T 1
#define HAVE_WCRTOMB 1
#define HAVE_WCTYPE_H 1
#define STDC_HEADERS 1
#ifndef UNIX
#define UNIX 1
#endif

/* - Derived settings (as in the configure-generated header) */
#define AUTOCONF 1
#if !defined(HAVE_BOOL) && !defined(bool)
#define bool  char
#define true  1
#define false 0
#endif
#if ! defined(HAVE_WCHAR_T)
#define HAS_WCHAR 0
#define HAS_WCTYPE 0
#define HAS_MBSTATE 0
#else
#define HAS_WCHAR 1
#if defined(HAVE_WCTYPE_H) && defined(HAVE_ISWSPACE)
#define HAS_WCTYPE 1
#endif
#if defined(HAVE_MBSTATE_T) && defined(HAVE_WCRTOMB)
#define HAS_MBSTATE 1
#endif
#endif
#define HAS_ICONV 0
#define HAS_CTRL_C_IN_ERR_MSG 1
#ifndef HAVE_MEMBER_TEMPLATES
#define GCONTAINER_NO_MEMBER_TEMPLATES 1
#endif
#ifndef HAVE_TYPENAME
#define GCONTAINER_NO_TYPENAME 1
#endif
#endif
