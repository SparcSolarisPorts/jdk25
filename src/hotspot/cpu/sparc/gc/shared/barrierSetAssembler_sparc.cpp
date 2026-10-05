/*
 * Copyright (c) 2018, 2023, Oracle and/or its affiliates. All rights reserved.
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

#include "gc/shared/barrierSet.hpp"
#include "asm/macroAssembler.inline.hpp"
#include "gc/shared/barrierSetAssembler.hpp"
#include "interpreter/interp_masm.hpp"
#include "runtime/jniHandles.hpp"
#ifdef COMPILER2
#include "gc/shared/c2/barrierSetC2.hpp"
#include "runtime/frame.hpp"
#endif // COMPILER2

#define __ masm->

void BarrierSetAssembler::store_at(MacroAssembler* masm, DecoratorSet decorators, BasicType type,
                                   Register val, Address dst, Register tmp) {
  bool in_heap = (decorators & IN_HEAP) != 0;
  bool in_native = (decorators & IN_NATIVE) != 0;
  bool is_not_null = (decorators & IS_NOT_NULL) != 0;

  switch (type) {
  case T_ARRAY:
  case T_OBJECT: {
    if (in_heap) {
      if (dst.has_disp() && !Assembler::is_simm13(dst.disp())) {
        assert(!dst.has_index(), "not supported yet");
        __ set(dst.disp(), tmp);
        dst = Address(dst.base(), tmp);
      }
      if (UseCompressedOops) {
        assert(dst.base() != val, "not enough registers");
        if (is_not_null) {
          __ encode_heap_oop_not_null(val);
        } else {
          __ encode_heap_oop(val);
        }
        __ st(val, dst);
      } else {
        __ st_ptr(val, dst);
      }
    } else {
      assert(in_native, "why else?");
      __ st_ptr(val, dst);
    }
    break;
  }
  case T_ADDRESS:
    __ st_ptr(val, dst);
    break;
  default: ShouldNotReachHere(); // other primitive types are handled elsewhere
  }
}

void BarrierSetAssembler::load_at(MacroAssembler* masm, DecoratorSet decorators, BasicType type,
                                  Address src, Register dst, Register tmp) {
  bool in_heap = (decorators & IN_HEAP) != 0;
  bool in_native = (decorators & IN_NATIVE) != 0;
  bool is_not_null = (decorators & IS_NOT_NULL) != 0;

  switch (type) {
  case T_ARRAY:
  case T_OBJECT: {
    if (in_heap) {
      if (src.has_disp() && !Assembler::is_simm13(src.disp())) {
        assert(!src.has_index(), "not supported yet");
        __ set(src.disp(), tmp);
        src = Address(src.base(), tmp);
      }
      if (UseCompressedOops) {
        __ lduw(src, dst);
        if (is_not_null) {
          __ decode_heap_oop_not_null(dst);
        } else {
          __ decode_heap_oop(dst);
        }
      } else {
        __ ld_ptr(src, dst);
      }
    } else {
      assert(in_native, "why else?");
      __ ld_ptr(src, dst);
    }
    break;
  }
  case T_ADDRESS:
    __ ld_ptr(src, dst);
    break;
  default: ShouldNotReachHere(); // other primitive types are handled elsewhere
  }
}

void BarrierSetAssembler::try_resolve_jobject_in_native(MacroAssembler* masm, Register jni_env,
                                                        Register obj, Register tmp, Label& slowpath) {
  __ andn(obj, JNIHandles::tag_mask, obj);
  __ ld_ptr(obj, 0, obj);
}

#ifdef COMPILER2

OptoReg::Name BarrierSetAssembler::refine_register(const Node* node, OptoReg::Name opto_reg) {
  if (!OptoReg::is_reg(opto_reg)) {
    return OptoReg::Bad;
  }

  const VMReg vm_reg = OptoReg::as_VMReg(opto_reg);
  // 64-bit integer registers are represented by a pair of adjacent OptoReg
  // slots; the odd slot denotes the upper half of the register, not a
  // separate register, so filter it out. Float registers are 32-bit wide on
  // SPARC, hence every OptoReg slot in the float range is a real, distinct
  // register that must be preserved individually.
  if (vm_reg->is_Register() && (opto_reg & 1) != 0) {
    return OptoReg::Bad;
  }

  return opto_reg;
}

#undef __
#define __ _masm->

SaveLiveRegisters::SaveLiveRegisters(MacroAssembler *masm, BarrierStubC2 *stub)
  : _masm(masm), _reg_mask(stub->preserve_set()) {

  const int register_save_size = iterate_over_register_mask(ACTION_COUNT_ONLY) * BytesPerWord;
  _frame_size = align_up(frame::register_save_words * BytesPerWord + register_save_size,
                         2 * BytesPerWord);

  // Push a frame without rotating the register windows; keep the register
  // window spill area (frame::register_save_words) at the bottom of the new
  // frame free for the callee, as mandated by the SPARC ABI.
  __ sub(SP, _frame_size, SP);

  iterate_over_register_mask(ACTION_SAVE);
}

SaveLiveRegisters::~SaveLiveRegisters() {
  iterate_over_register_mask(ACTION_RESTORE);

  __ add(SP, _frame_size, SP);
}

int SaveLiveRegisters::iterate_over_register_mask(IterationAction action) {
  int reg_save_index = 0;
  RegMaskIterator live_regs_iterator(_reg_mask);

  while (live_regs_iterator.has_next()) {
    const OptoReg::Name opto_reg = live_regs_iterator.next();

    // Filter out stack slots (spilled registers, i.e., stack-allocated registers).
    if (!OptoReg::is_reg(opto_reg)) {
      continue;
    }

    const VMReg vm_reg = OptoReg::as_VMReg(opto_reg);
    const int offset = frame::register_save_words * BytesPerWord + STACK_BIAS +
                       reg_save_index * BytesPerWord;

    if (vm_reg->is_Register()) {
      assert((opto_reg & 1) == 0, "odd register halves are filtered out by refine_register");
      const Register reg = vm_reg->as_Register();

      if (action == ACTION_SAVE) {
        __ stx(reg, SP, offset);
      } else if (action == ACTION_RESTORE) {
        __ ldx(SP, offset, reg);
      }
    } else {
      assert(vm_reg->is_FloatRegister(), "unexpected register type");
      const FloatRegister reg = vm_reg->as_FloatRegister();

      // Save each 32-bit float register individually; this also covers the
      // even/odd register pairs that make up double values.
      if (action == ACTION_SAVE) {
        __ stf(FloatRegisterImpl::S, reg, SP, offset);
      } else if (action == ACTION_RESTORE) {
        __ ldf(FloatRegisterImpl::S, SP, offset, reg);
      }
    }

    reg_save_index++;
  }

  return reg_save_index;
}

#endif // COMPILER2
