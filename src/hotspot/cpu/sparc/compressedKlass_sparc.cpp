/*
 * Copyright (c) 2026, SPARC port contributors. All rights reserved.
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
 * You should have received a copy of the GNU General Public License
 * version 2 along with this work; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
 * or visit www.oracle.com if you need additional information or have any
 * questions.
 *
 */

#include "memory/metaspace.hpp"
#include "oops/compressedKlass.hpp"
#include "utilities/globalDefinitions.hpp"

// Prefer a zero-based encoding above the brk heap. Do not probe below 4G:
// reserving class space there can obstruct later Solaris malloc growth.
char* CompressedKlassPointers::reserve_address_space_for_compressed_classes(size_t size, bool aslr, bool optimize_for_zero_base) {
  if (optimize_for_zero_base) {
    // This helper probes [4G, 32G), preserving native-heap headroom while
    // allowing zero-based klass decoding independently of compressed oops.
    return reserve_address_space_for_zerobased_encoding(size, aslr);
  }
  return nullptr;
}
