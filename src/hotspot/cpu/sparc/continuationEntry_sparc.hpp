/*
 * Copyright (c) 2022, Oracle and/or its affiliates. All rights reserved.
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

#ifndef CPU_SPARC_CONTINUATIONENTRY_SPARC_HPP
#define CPU_SPARC_CONTINUATIONENTRY_SPARC_HPP

// ContinuationEntry starts at the unbiased stack pointer. Keep the V9
// register-window spill area and the six outgoing argument home slots free.
// A flushw or an ABI callee must never overwrite continuation metadata.
class ContinuationEntryPD {
  intptr_t _abi_save_area[22];
  address _resume_pc;
  intptr_t* _thaw_bottom;
 public:
  static ByteSize resume_pc_offset() { return byte_offset_of(ContinuationEntryPD, _resume_pc); }
  static ByteSize thaw_bottom_offset() { return byte_offset_of(ContinuationEntryPD, _thaw_bottom); }
  address resume_pc() const { return _resume_pc; }
  void set_resume_pc(address pc) { _resume_pc = pc; }
  void set_thaw_bottom(intptr_t* sp) { _thaw_bottom = sp; }
};

#endif // CPU_SPARC_CONTINUATIONENTRY_SPARC_HPP
