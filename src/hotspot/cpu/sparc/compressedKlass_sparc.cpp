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

// SPARC has no small-immediate advantages for any particular base address
// range (the narrow-klass base is always materialized with a full 64-bit
// set), so we only attempt the zero-based encoding reservation, which
// allows the base to be zero and the encoding to be a plain shift.
char* CompressedKlassPointers::reserve_address_space_for_compressed_classes(size_t size, bool aslr, bool optimize_for_zero_base) {

  char* result = nullptr;

  if (optimize_for_zero_base) {
    // Failing that, if we are running without CDS, attempt to allocate below 32G.
    // This allows us to use zero-based encoding with a non-zero shift.
    result = reserve_address_space_for_zerobased_encoding(size, aslr);
  }

  return result;
}
