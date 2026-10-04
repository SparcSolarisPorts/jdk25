/*
 * Copyright (c) 1997, 2025, Oracle and/or its affiliates. All rights reserved.
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

#ifndef CPU_SPARC_STUBROUTINES_SPARC_HPP
#define CPU_SPARC_STUBROUTINES_SPARC_HPP

// This file holds the platform specific parts of the StubRoutines
// definition. See stubRoutines.hpp for a description on how to
// extend it.


// So unfortunately c2 will call with a pc from a frame object
// (already adjusted) and a raw pc (unadjusted), so we need to check both.
// It didn't use to be like this before adapter removal.
static bool returns_to_call_stub(address return_pc)   {
  return ((return_pc + frame::pc_return_offset) == _call_stub_return_address) ||
          (return_pc == _call_stub_return_address );
}

// emit enum used to size per-blob code buffers

#define DEFINE_BLOB_SIZE(blob_name, size) \
  _ ## blob_name ## _code_size = size,

enum platform_dependent_constants {
  STUBGEN_ARCH_BLOBS_DO(DEFINE_BLOB_SIZE)
};

#undef DEFINE_BLOB_SIZE

class Sparc {
 friend class StubGenerator;

  // declare fields for arch-specific entries

#define DECLARE_ARCH_ENTRY(arch, blob_name, stub_name, field_name, getter_name) \
  static address STUB_FIELD_NAME(field_name) ;

#define DECLARE_ARCH_ENTRY_INIT(arch, blob_name, stub_name, field_name, getter_name, init_function) \
  DECLARE_ARCH_ENTRY(arch, blob_name, stub_name, field_name, getter_name)

private:
  STUBGEN_ARCH_ENTRIES_DO(DECLARE_ARCH_ENTRY, DECLARE_ARCH_ENTRY_INIT)

#undef DECLARE_ARCH_ENTRY_INIT
#undef DECLARE_ARCH_ENTRY

  // define getters for arch-specific entries

#define DEFINE_ARCH_ENTRY_GETTER(arch, blob_name, stub_name, field_name, getter_name) \
  static address getter_name() { return STUB_FIELD_NAME(field_name); }

#define DEFINE_ARCH_ENTRY_GETTER_INIT(arch, blob_name, stub_name, field_name, getter_name, init_function) \
  DEFINE_ARCH_ENTRY_GETTER(arch, blob_name, stub_name, field_name, getter_name)

public:
  STUBGEN_ARCH_ENTRIES_DO(DEFINE_ARCH_ENTRY_GETTER, DEFINE_ARCH_ENTRY_GETTER_INIT)

#undef DEFINE_ARCH_ENTRY_GETTER_INIT
#undef DEFINE_ARCH_ENTRY_GETTER

 private:
  static address _test_stop_entry;
  static address _stop_subroutine_entry;
  static address _flush_callers_register_windows_entry;

  // masks and table for CRC32
  static const uint64_t _crc_by128_masks[];
  static const juint    _crc_table[];
  static juint    _crc32c_table[];

 public:
  // test assembler stop routine by setting registers
  static void (*test_stop_entry()) ()                     { return CAST_TO_FN_PTR(void (*)(void), _test_stop_entry); }

  // a subroutine for debugging assembler code
  static address stop_subroutine_entry_address()          { return (address)&_stop_subroutine_entry; }

  // flushes (all but current) register window
  static intptr_t* (*flush_callers_register_windows_func())() { return CAST_TO_FN_PTR(intptr_t* (*)(void), _flush_callers_register_windows_entry); }

  static address crc_by128_masks_addr()  { return (address)_crc_by128_masks; }
};

#endif // CPU_SPARC_STUBROUTINES_SPARC_HPP
