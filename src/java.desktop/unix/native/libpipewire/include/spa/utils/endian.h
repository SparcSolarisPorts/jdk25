/* Spa */
/* SPDX-FileCopyrightText: Copyright © 2019 Wim Taymans */
/* SPDX-License-Identifier: MIT */

#ifndef SPA_ENDIAN_H
#define SPA_ENDIAN_H

#if defined(__FreeBSD__) || defined(__MidnightBSD__)
#include <sys/endian.h>
#define bswap_16 bswap16
#define bswap_32 bswap32
#define bswap_64 bswap64
#elif defined(_MSC_VER) && defined(_WIN32)
#include <stdlib.h>
#define __LITTLE_ENDIAN 1234
#define __BIG_ENDIAN 4321
#define __BYTE_ORDER __LITTLE_ENDIAN
#define bswap_16 _byteswap_ushort
#define bswap_32 _byteswap_ulong
#define bswap_64 _byteswap_uint64
#elif defined(SOLARIS)
/* Solaris has no endian.h or byteswap.h; define the byte order macros here. */
#define __LITTLE_ENDIAN 1234
#define __BIG_ENDIAN 4321
#if defined(__sparc)
#define __BYTE_ORDER __BIG_ENDIAN
#else
#define __BYTE_ORDER __LITTLE_ENDIAN
#endif
#else
#include <endian.h>
#include <byteswap.h>
#endif

#endif /* SPA_ENDIAN_H */
