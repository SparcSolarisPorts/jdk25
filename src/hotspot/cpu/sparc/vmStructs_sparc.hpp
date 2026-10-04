/*
 * Copyright (c) 2001, 2025, Oracle and/or its affiliates. All rights reserved.
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
 * You should have received a copy of the GNU General Public License version
 * 2 along with this work; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA.
 *
 * Please contact Oracle, 500 Oracle Parkway, Redwood Shores, CA 94065 USA
 * or visit www.oracle.com if you need additional information or have any
 * questions.
 *
 */

#ifndef CPU_SPARC_VMSTRUCTS_SPARC_HPP
#define CPU_SPARC_VMSTRUCTS_SPARC_HPP

// These are the CPU-specific fields, types and integer
// constants required by the Serviceability Agent. This file is
// referenced by vmStructs.cpp.

#define VM_STRUCTS_CPU(nonstatic_field, static_field, unchecked_nonstatic_field, volatile_nonstatic_field, nonproduct_nonstatic_field) \
  volatile_nonstatic_field(JavaFrameAnchor, _flags, int)

#define VM_TYPES_CPU(declare_type, declare_toplevel_type, declare_oop_type, declare_integer_type, declare_unsigned_integer_type)

#define VM_INT_CONSTANTS_CPU(declare_constant, declare_preprocessor_constant) \
  declare_constant(VM_Version::ISA_V9)                  \
  declare_constant(VM_Version::ISA_POPC)                \
  declare_constant(VM_Version::ISA_VIS1)                \
  declare_constant(VM_Version::ISA_VIS2)                \
  declare_constant(VM_Version::ISA_BLK_INIT)            \
  declare_constant(VM_Version::ISA_FMAF)                \
  declare_constant(VM_Version::ISA_VIS3)                \
  declare_constant(VM_Version::ISA_HPC)                 \
  declare_constant(VM_Version::ISA_IMA)                 \
  declare_constant(VM_Version::ISA_AES)                 \
  declare_constant(VM_Version::ISA_DES)                 \
  declare_constant(VM_Version::ISA_KASUMI)              \
  declare_constant(VM_Version::ISA_CAMELLIA)            \
  declare_constant(VM_Version::ISA_MD5)                 \
  declare_constant(VM_Version::ISA_SHA1)                \
  declare_constant(VM_Version::ISA_SHA256)              \
  declare_constant(VM_Version::ISA_SHA512)              \
  declare_constant(VM_Version::ISA_MPMUL)               \
  declare_constant(VM_Version::ISA_MONT)                \
  declare_constant(VM_Version::ISA_PAUSE)               \
  declare_constant(VM_Version::ISA_CBCOND)              \
  declare_constant(VM_Version::ISA_CRC32C)              \
  declare_constant(VM_Version::ISA_VIS3B)               \
  declare_constant(VM_Version::ISA_ADI)                 \
  declare_constant(VM_Version::ISA_SPARC5)              \
  declare_constant(VM_Version::ISA_MWAIT)               \
  declare_constant(VM_Version::ISA_XMPMUL)              \
  declare_constant(VM_Version::ISA_XMONT)               \
  declare_constant(VM_Version::ISA_PAUSE_NSEC)          \
  declare_constant(VM_Version::ISA_VAMASK)              \
  declare_constant(VM_Version::ISA_SPARC6)              \
  declare_constant(VM_Version::ISA_DICTUNP)             \
  declare_constant(VM_Version::ISA_FPCMPSHL)            \
  declare_constant(VM_Version::ISA_RLE)                 \
  declare_constant(VM_Version::ISA_SHA3)                \
  declare_constant(VM_Version::ISA_VIS3C)               \
  declare_constant(VM_Version::ISA_SPARC5B)             \
  declare_constant(VM_Version::ISA_MME)                 \
  declare_constant(VM_Version::CPU_FAST_IDIV)           \
  declare_constant(VM_Version::CPU_FAST_RDPC)           \
  declare_constant(VM_Version::CPU_FAST_BIS)            \
  declare_constant(VM_Version::CPU_FAST_LD)             \
  declare_constant(VM_Version::CPU_FAST_CMOVE)          \
  declare_constant(VM_Version::CPU_FAST_IND_BR)         \
  declare_constant(VM_Version::CPU_BLK_ZEROING)

#define VM_LONG_CONSTANTS_CPU(declare_constant, declare_preprocessor_constant)

#endif // CPU_SPARC_VMSTRUCTS_SPARC_HPP
