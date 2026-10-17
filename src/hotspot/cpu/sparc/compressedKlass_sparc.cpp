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
#include "runtime/os.hpp"
#include "utilities/globalDefinitions.hpp"

// Try unscaled encoding below 4G first. The previous native-heap obstruction
// was at 0x10c000000, above 4G, not in this range. A reservation wholly below
// 4G does not occupy that Solaris LP64 brk growth area.
char* CompressedKlassPointers::reserve_address_space_for_compressed_classes(size_t size, bool aslr, bool optimize_for_zero_base) {
  if (optimize_for_zero_base) {
    char* result = reserve_address_space_for_unscaled_encoding(size, aslr);
    if (result != nullptr) {
      return result;
    }
    result = reserve_address_space_for_zerobased_encoding(size, aslr);
    if (result != nullptr) {
      return result;
    }
  }

  // In the CDS relocation path the mapping start is also the prescribed
  // encoding base; rebasing it would invalidate archived narrow Klass IDs.
  // Reserve a full encoding window so the OS places that base far enough
  // below the top of user address space, then immediately release the unused
  // tail. Only the requested class/archive space remains reserved; no physical
  // memory is committed by this placement reservation.
  const size_t reserve_size = MAX2(size, max_encoding_range_size());
  char* result = os::reserve_memory_aligned(reserve_size, Metaspace::reserve_alignment(), mtClass);
  if (result != nullptr && reserve_size > size) {
    guarantee(os::release_memory(result + size, reserve_size - size),
              "Could not release unused SPARC class encoding window");
  }
  return result;
}
