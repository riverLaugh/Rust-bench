#!/bin/bash
set -uxo pipefail
git config --global --add safe.directory /testbed
cd /testbed
git apply -v - <<'EOF_114329324912'
diff --git a/.github/workflows/rust.yml b/.github/workflows/rust.yml
--- a/.github/workflows/rust.yml
+++ b/.github/workflows/rust.yml
@@ -46,8 +46,17 @@ jobs:
         profile: minimal
         toolchain: ${{ matrix.channel }}-${{ matrix.rust_target }}
 
-    - name: Tests
-      run: cargo test --features example_generated
+    - name: Install cargo-hack
+      run: cargo install cargo-hack
+
+    - name: Powerset
+      run: cargo hack test --feature-powerset --lib --optional-deps "serde" --depth 3 --skip rustc-dep-of-std
+
+    - name: Docs
+      run: cargo doc --features example_generated
+
+    - name: Smoke test
+      run: cargo run --manifest-path tests/smoke-test/Cargo.toml
 
   embedded:
     name: Build (embedded)
diff --git a/Cargo.toml b/Cargo.toml
--- a/Cargo.toml
+++ b/Cargo.toml
@@ -16,16 +16,16 @@ categories = ["no-std"]
 description = """
 A macro to generate structures which behave like bitflags.
 """
-exclude = ["bors.toml"]
+exclude = ["tests", ".github"]
 
 [dependencies]
-core = { version = '1.0.0', optional = true, package = 'rustc-std-workspace-core' }
-compiler_builtins = { version = '0.1.2', optional = true }
+serde = { version = "1.0", optional = true }
+core = { version = "1.0.0", optional = true, package = "rustc-std-workspace-core" }
+compiler_builtins = { version = "0.1.2", optional = true }
 
 [dev-dependencies]
 trybuild = "1.0"
 rustversion = "1.0"
-serde = "1.0"
 serde_derive = "1.0"
 serde_json = "1.0"
 
diff --git a/src/lib.rs b/src/lib.rs
--- a/src/lib.rs
+++ b/src/lib.rs
@@ -845,181 +801,421 @@ macro_rules! __impl_bitflags {
             }
         }
 
-        impl $crate::BitFlags for $BitFlags {
+        impl $crate::BitFlags for $PublicBitFlags {
             type Bits = $T;
 
             fn empty() -> Self {
-                $BitFlags::empty()
+                $PublicBitFlags::empty()
             }
 
             fn all() -> Self {
-                $BitFlags::all()
+                $PublicBitFlags::all()
             }
 
             fn bits(&self) -> $T {
-                $BitFlags::bits(self)
+                $PublicBitFlags::bits(self)
             }
 
-            fn from_bits(bits: $T) -> $crate::__private::core::option::Option<$BitFlags> {
-                $BitFlags::from_bits(bits)
+            fn from_bits(bits: $T) -> $crate::__private::core::option::Option<$PublicBitFlags> {
+                $PublicBitFlags::from_bits(bits)
             }
 
-            fn from_bits_truncate(bits: $T) -> $BitFlags {
-                $BitFlags::from_bits_truncate(bits)
+            fn from_bits_truncate(bits: $T) -> $PublicBitFlags {
+                $PublicBitFlags::from_bits_truncate(bits)
             }
 
-            unsafe fn from_bits_unchecked(bits: $T) -> $BitFlags {
-                $BitFlags::from_bits_unchecked(bits)
+            fn from_bits_retain(bits: $T) -> $PublicBitFlags {
+                $PublicBitFlags::from_bits_retain(bits)
             }
 
             fn is_empty(&self) -> bool {
-                $BitFlags::is_empty(self)
+                $PublicBitFlags::is_empty(self)
             }
 
             fn is_all(&self) -> bool {
-                $BitFlags::is_all(self)
+                $PublicBitFlags::is_all(self)
             }
 
-            fn intersects(&self, other: $BitFlags) -> bool {
-                $BitFlags::intersects(self, other)
+            fn intersects(&self, other: $PublicBitFlags) -> bool {
+                $PublicBitFlags::intersects(self, other)
             }
 
-            fn contains(&self, other: $BitFlags) -> bool {
-                $BitFlags::contains(self, other)
+            fn contains(&self, other: $PublicBitFlags) -> bool {
+                $PublicBitFlags::contains(self, other)
             }
 
-            fn insert(&mut self, other: $BitFlags) {
-                $BitFlags::insert(self, other)
+            fn insert(&mut self, other: $PublicBitFlags) {
+                $PublicBitFlags::insert(self, other)
             }
 
-            fn remove(&mut self, other: $BitFlags) {
-                $BitFlags::remove(self, other)
+            fn remove(&mut self, other: $PublicBitFlags) {
+                $PublicBitFlags::remove(self, other)
             }
 
-            fn toggle(&mut self, other: $BitFlags) {
-                $BitFlags::toggle(self, other)
+            fn toggle(&mut self, other: $PublicBitFlags) {
+                $PublicBitFlags::toggle(self, other)
             }
 
-            fn set(&mut self, other: $BitFlags, value: bool) {
-                $BitFlags::set(self, other, value)
+            fn set(&mut self, other: $PublicBitFlags, value: bool) {
+                $PublicBitFlags::set(self, other, value)
             }
         }
 
-        impl $crate::__private::ImplementedByBitFlagsMacro for $BitFlags {}
+        impl $crate::__private::ImplementedByBitFlagsMacro for $PublicBitFlags {}
     };
+}
 
-    // Every attribute that the user writes on a const is applied to the
-    // corresponding const that we generate, but within the implementation of
-    // Debug and all() we want to ignore everything but #[cfg] attributes. In
-    // particular, including a #[deprecated] attribute on those items would fail
-    // to compile.
-    // https://github.com/bitflags/bitflags/issues/109
-    //
-    // Input:
-    //
-    //     ? #[cfg(feature = "advanced")]
-    //     ? #[deprecated(note = "Use something else.")]
-    //     ? #[doc = r"High quality documentation."]
-    //     fn f() -> i32 { /* ... */ }
-    //
-    // Output:
-    //
-    //     #[cfg(feature = "advanced")]
-    //     fn f() -> i32 { /* ... */ }
+/// Implement functions on the private (bitflags-facing) bitflags type.
+///
+/// Methods and trait implementations can be freely added here without breaking end-users.
+/// If we want to expose new functionality to `#[derive]`, this is the place to do it.
+#[macro_export(local_inner_macros)]
+#[doc(hidden)]
+macro_rules! __impl_internal_bitflags {
     (
-        $(#[$filtered:meta])*
-        ? #[cfg $($cfgargs:tt)*]
-        $(? #[$rest:ident $($restargs:tt)*])*
-        fn $($item:tt)*
-    ) => {
-        __impl_bitflags! {
-            $(#[$filtered])*
-            #[cfg $($cfgargs)*]
-            $(? #[$rest $($restargs)*])*
-            fn $($item)*
+        $InternalBitFlags:ident: $T:ty {
+            $(
+                $(#[$attr:ident $($args:tt)*])*
+                $Flag:ident;
+            )*
         }
-    };
-    (
-        $(#[$filtered:meta])*
-        // $next != `cfg`
-        ? #[$next:ident $($nextargs:tt)*]
-        $(? #[$rest:ident $($restargs:tt)*])*
-        fn $($item:tt)*
     ) => {
-        __impl_bitflags! {
-            $(#[$filtered])*
-            // $next filtered out
-            $(? #[$rest $($restargs)*])*
-            fn $($item)*
+        // Any new library traits impls should be added here
+        __impl_internal_bitflags_serde! {
+            $InternalBitFlags: $T {
+                $(
+                    $(#[$attr $($args)*])*
+                    $Flag;
+                )*
+            }
         }
-    };
-    (
-        $(#[$filtered:meta])*
-        fn $($item:tt)*
-    ) => {
-        $(#[$filtered])*
-        fn $($item)*
-    };
 
-    // Every attribute that the user writes on a const is applied to the
-    // corresponding const that we generate, but within the implementation of
-    // Debug and all() we want to ignore everything but #[cfg] attributes. In
-    // particular, including a #[deprecated] attribute on those items would fail
-    // to compile.
-    // https://github.com/bitflags/bitflags/issues/109
-    //
-    // const version
-    //
-    // Input:
-    //
-    //     ? #[cfg(feature = "advanced")]
-    //     ? #[deprecated(note = "Use something else.")]
-    //     ? #[doc = r"High quality documentation."]
-    //     const f: i32 { /* ... */ }
-    //
-    // Output:
-    //
-    //     #[cfg(feature = "advanced")]
-    //     const f: i32 { /* ... */ }
-    (
-        $(#[$filtered:meta])*
-        ? #[cfg $($cfgargs:tt)*]
-        $(? #[$rest:ident $($restargs:tt)*])*
-        const $($item:tt)*
-    ) => {
-        __impl_bitflags! {
-            $(#[$filtered])*
-            #[cfg $($cfgargs)*]
-            $(? #[$rest $($restargs)*])*
-            const $($item)*
+        impl $crate::__private::core::default::Default for $InternalBitFlags {
+            #[inline]
+            fn default() -> Self {
+                $InternalBitFlags::empty()
+            }
+        }
+
+        impl $crate::__private::core::fmt::Debug for $InternalBitFlags {
+            fn fmt(&self, f: &mut $crate::__private::core::fmt::Formatter) -> $crate::__private::core::fmt::Result {
+                // Iterate over the valid flags
+                let mut first = true;
+                for (name, _) in self.iter() {
+                    if !first {
+                        f.write_str(" | ")?;
+                    }
+
+                    first = false;
+                    f.write_str(name)?;
+                }
+
+                // Append any extra bits that correspond to flags to the end of the format
+                let extra_bits = self.bits & !Self::all().bits;
+
+                if extra_bits != <$T as $crate::__private::Bits>::EMPTY {
+                    if !first {
+                        f.write_str(" | ")?;
+                    }
+                    first = false;
+                    $crate::__private::core::write!(f, "{:#x}", extra_bits)?;
+                }
+
+                if first {
+                    f.write_str("empty")?;
+                }
+
+                $crate::__private::core::fmt::Result::Ok(())
+            }
+        }
+
+        impl $crate::__private::core::fmt::Binary for $InternalBitFlags {
+            fn fmt(&self, f: &mut $crate::__private::core::fmt::Formatter) -> $crate::__private::core::fmt::Result {
+                $crate::__private::core::fmt::Binary::fmt(&self.bits(), f)
+            }
+        }
+
+        impl $crate::__private::core::fmt::Octal for $InternalBitFlags {
+            fn fmt(&self, f: &mut $crate::__private::core::fmt::Formatter) -> $crate::__private::core::fmt::Result {
+                $crate::__private::core::fmt::Octal::fmt(&self.bits(), f)
+            }
+        }
+
+        impl $crate::__private::core::fmt::LowerHex for $InternalBitFlags {
+            fn fmt(&self, f: &mut $crate::__private::core::fmt::Formatter) -> $crate::__private::core::fmt::Result {
+                $crate::__private::core::fmt::LowerHex::fmt(&self.bits(), f)
+            }
+        }
+
+        impl $crate::__private::core::fmt::UpperHex for $InternalBitFlags {
+            fn fmt(&self, f: &mut $crate::__private::core::fmt::Formatter) -> $crate::__private::core::fmt::Result {
+                $crate::__private::core::fmt::UpperHex::fmt(&self.bits(), f)
+            }
+        }
+
+        #[allow(
+            dead_code,
+            deprecated,
+            unused_doc_comments,
+            unused_attributes,
+            unused_mut,
+            non_upper_case_globals
+        )]
+        impl $InternalBitFlags {
+            #[inline]
+            pub const fn empty() -> Self {
+                Self { bits: <$T as $crate::__private::Bits>::EMPTY }
+            }
+
+            #[inline]
+            pub const fn all() -> Self {
+                Self::from_bits_truncate(<$T as $crate::__private::Bits>::ALL)
+            }
+
+            #[inline]
+            pub const fn bits(&self) -> $T {
+                self.bits
+            }
+
+            #[inline]
+            pub fn bits_mut(&mut self) -> &mut $T {
+                &mut self.bits
+            }
+
+            #[inline]
+            pub const fn from_bits(bits: $T) -> $crate::__private::core::option::Option<Self> {
+                let truncated = Self::from_bits_truncate(bits).bits;
+
+                if truncated == bits {
+                    $crate::__private::core::option::Option::Some(Self { bits })
+                } else {
+                    $crate::__private::core::option::Option::None
+                }
+            }
+
+            #[inline]
+            pub const fn from_bits_truncate(bits: $T) -> Self {
+                if bits == <$T as $crate::__private::Bits>::EMPTY {
+                    return Self { bits }
+                }
+
+                let mut truncated = <$T as $crate::__private::Bits>::EMPTY;
+
+                $(
+                    $(#[$attr $($args)*])*
+                    if bits & <$InternalBitFlags as $crate::__private::InternalFlags>::PublicFlags::$Flag.bits() == <$InternalBitFlags as $crate::__private::InternalFlags>::PublicFlags::$Flag.bits() {
+                        truncated |= <$InternalBitFlags as $crate::__private::InternalFlags>::PublicFlags::$Flag.bits()
+                    }
+                )*
+
+                Self { bits: truncated }
+            }
+
+            #[inline]
+            pub const fn from_bits_retain(bits: $T) -> Self {
+                Self { bits }
+            }
+
+            #[inline]
+            pub const fn is_empty(&self) -> bool {
+                self.bits == Self::empty().bits
+            }
+
+            #[inline]
+            pub const fn is_all(&self) -> bool {
+                Self::all().bits | self.bits == self.bits
+            }
+
+            #[inline]
+            pub const fn intersects(&self, other: Self) -> bool {
+                !(Self { bits: self.bits & other.bits}).is_empty()
+            }
+
+            #[inline]
+            pub const fn contains(&self, other: Self) -> bool {
+                (self.bits & other.bits) == other.bits
+            }
+
+            #[inline]
+            pub fn insert(&mut self, other: Self) {
+                self.bits |= other.bits;
+            }
+
+            #[inline]
+            pub fn remove(&mut self, other: Self) {
+                self.bits &= !other.bits;
+            }
+
+            #[inline]
+            pub fn toggle(&mut self, other: Self) {
+                self.bits ^= other.bits;
+            }
+
+            #[inline]
+            pub fn set(&mut self, other: Self, value: bool) {
+                if value {
+                    self.insert(other);
+                } else {
+                    self.remove(other);
+                }
+            }
+
+            #[inline]
+            #[must_use]
+            pub const fn intersection(self, other: Self) -> Self {
+                Self { bits: self.bits & other.bits }
+            }
+
+            #[inline]
+            #[must_use]
+            pub const fn union(self, other: Self) -> Self {
+                Self { bits: self.bits | other.bits }
+            }
+
+            #[inline]
+            #[must_use]
+            pub const fn difference(self, other: Self) -> Self {
+                Self { bits: self.bits & !other.bits }
+            }
+
+            #[inline]
+            #[must_use]
+            pub const fn symmetric_difference(self, other: Self) -> Self {
+                Self { bits: self.bits ^ other.bits }
+            }
+
+            #[inline]
+            #[must_use]
+            pub const fn complement(self) -> Self {
+                Self::from_bits_truncate(!self.bits)
+            }
+
+            pub fn iter(self) -> impl $crate::__private::core::iter::Iterator<Item = (&'static str, $T)> {
+                use $crate::__private::core::iter::Iterator as _;
+
+                const NUM_FLAGS: usize = {
+                    let mut num_flags = 0;
+
+                    $(
+                        $(#[$attr $($args)*])*
+                        {
+                            num_flags += 1;
+                        }
+                    )*
+
+                    num_flags
+                };
+
+                const OPTIONS: [$T; NUM_FLAGS] = [
+                    $(
+                        $(#[$attr $($args)*])*
+                        <$InternalBitFlags as $crate::__private::InternalFlags>::PublicFlags::$Flag.bits(),
+                    )*
+                ];
+
+                const OPTIONS_NAMES: [&'static str; NUM_FLAGS] = [
+                    $(
+                        $(#[$attr $($args)*])*
+                        $crate::__private::core::stringify!($Flag),
+                    )*
+                ];
+
+                let mut start = 0;
+                let mut state = self;
+
+                $crate::__private::core::iter::from_fn(move || {
+                    if state.is_empty() || NUM_FLAGS == 0 {
+                        $crate::__private::core::option::Option::None
+                    } else {
+                        for (flag, flag_name) in OPTIONS[start..NUM_FLAGS].iter().copied()
+                            .zip(OPTIONS_NAMES[start..NUM_FLAGS].iter().copied())
+                        {
+                            start += 1;
+
+                            // NOTE: We check whether the flag exists in self, but remove it from
+                            // a different value. This ensure that overlapping flags are handled
+                            // properly. Take the following example:
+                            //
+                            // const A: 0b00000001;
+                            // const B: 0b00000101;
+                            //
+                            // Given the bits 0b00000101, both A and B are set. But if we removed A
+                            // as we encountered it we'd be left with 0b00000100, which doesn't
+                            // correspond to a valid flag on its own.
+                            if self.contains(Self { bits: flag }) {
+                                state.remove(Self { bits: flag });
+
+                                return $crate::__private::core::option::Option::Some((flag_name, flag))
+                            }
+                        }
+
+                        $crate::__private::core::option::Option::None
+                    }
+                })
+            }
         }
     };
+}
+
+// Optional features
+//
+// These macros implement additional library traits for the internal bitflags type so that
+// the end-user can either implement or derive those same traits based on the implementation
+// we provide in `bitflags`.
+//
+// These macros all follow a  similar pattern. If an optional feature of `bitflags` is enabled
+// they'll expand to some impl blocks based on a re-export of the library. If the optional feature
+// is not enabled then they expand to a no-op.
+
+/// Implement `Serialize` and `Deserialize` for the internal bitflags type.
+#[macro_export(local_inner_macros)]
+#[doc(hidden)]
+#[cfg(feature = "serde")]
+macro_rules! __impl_internal_bitflags_serde {
     (
-        $(#[$filtered:meta])*
-        // $next != `cfg`
-        ? #[$next:ident $($nextargs:tt)*]
-        $(? #[$rest:ident $($restargs:tt)*])*
-        const $($item:tt)*
+        $InternalBitFlags:ident: $T:ty {
+            $(
+                $(#[$attr:ident $($args:tt)*])*
+                $Flag:ident;
+            )*
+        }
     ) => {
-        __impl_bitflags! {
-            $(#[$filtered])*
-            // $next filtered out
-            $(? #[$rest $($restargs)*])*
-            const $($item)*
+        impl $crate::__private::serde::Serialize for $InternalBitFlags {
+            fn serialize<S: $crate::__private::serde::Serializer>(&self, serializer: S) -> $crate::__private::core::result::Result<S::Ok, S::Error> {
+                $crate::serde_support::serialize_bits_default($crate::__private::core::stringify!($InternalBitFlags), &self.bits, serializer)
+            }
         }
-    };
+
+        impl<'de> $crate::__private::serde::Deserialize<'de> for $InternalBitFlags {
+            fn deserialize<D: $crate::__private::serde::Deserializer<'de>>(deserializer: D) -> $crate::__private::core::result::Result<Self, D::Error> {
+                let bits = $crate::serde_support::deserialize_bits_default($crate::__private::core::stringify!($InternalBitFlags), deserializer)?;
+
+                $crate::__private::core::result::Result::Ok($InternalBitFlags::from_bits_retain(bits))
+            }
+        }
+    }
+}
+
+#[macro_export(local_inner_macros)]
+#[doc(hidden)]
+#[cfg(not(feature = "serde"))]
+macro_rules! __impl_internal_bitflags_serde {
     (
-        $(#[$filtered:meta])*
-        const $($item:tt)*
-    ) => {
-        $(#[$filtered])*
-        const $($item)*
-    };
+        $InternalBitFlags:ident: $T:ty {
+            $(
+                $(#[$attr:ident $($args:tt)*])*
+                $Flag:ident;
+            )*
+        }
+    ) => { }
 }
 
 #[cfg(feature = "example_generated")]
 pub mod example_generated;
 
+#[cfg(feature = "serde")]
+pub mod serde_support;
+
 #[cfg(test)]
 mod tests {
     use std::collections::hash_map::DefaultHasher;
diff --git a/src/lib.rs b/src/lib.rs
--- a/src/lib.rs
+++ b/src/lib.rs
@@ -1030,7 +1226,7 @@ mod tests {
         #[doc = "> you are the easiest person to fool."]
         #[doc = "> "]
         #[doc = "> - Richard Feynman"]
-        #[derive(Default)]
+        #[derive(Clone, Copy, Default, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
         struct Flags: u32 {
             const A = 0b00000001;
             #[doc = "<pcwalton> macros are way better at generating code than trans is"]
diff --git a/src/lib.rs b/src/lib.rs
--- a/src/lib.rs
+++ b/src/lib.rs
@@ -1039,28 +1235,32 @@ mod tests {
             #[doc = "* cmr bed"]
             #[doc = "* strcat table"]
             #[doc = "<strcat> wait what?"]
-            const ABC = Self::A.bits | Self::B.bits | Self::C.bits;
+            const ABC = Self::A.bits() | Self::B.bits() | Self::C.bits();
         }
 
+        #[derive(Clone, Copy, Default, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
         struct _CfgFlags: u32 {
             #[cfg(unix)]
             const _CFG_A = 0b01;
             #[cfg(windows)]
             const _CFG_B = 0b01;
             #[cfg(unix)]
-            const _CFG_C = Self::_CFG_A.bits | 0b10;
+            const _CFG_C = Self::_CFG_A.bits() | 0b10;
         }
 
+        #[derive(Clone, Copy, Default, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
         struct AnotherSetOfFlags: i8 {
             const ANOTHER_FLAG = -1_i8;
         }
 
+        #[derive(Clone, Copy, Default, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
         struct LongFlags: u32 {
             const LONG_A = 0b1111111111111111;
         }
     }
 
     bitflags! {
+        #[derive(Clone, Copy, Default, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
         struct EmptyFlags: u32 {
         }
     }
diff --git a/src/lib.rs b/src/lib.rs
--- a/src/lib.rs
+++ b/src/lib.rs
@@ -1113,28 +1313,28 @@ mod tests {
     }
 
     #[test]
-    fn test_from_bits_unchecked() {
-        let extra = unsafe { Flags::from_bits_unchecked(0b1000) };
-        assert_eq!(unsafe { Flags::from_bits_unchecked(0) }, Flags::empty());
-        assert_eq!(unsafe { Flags::from_bits_unchecked(0b1) }, Flags::A);
-        assert_eq!(unsafe { Flags::from_bits_unchecked(0b10) }, Flags::B);
+    fn test_from_bits_retain() {
+        let extra = Flags::from_bits_retain(0b1000);
+        assert_eq!(Flags::from_bits_retain(0), Flags::empty());
+        assert_eq!(Flags::from_bits_retain(0b1), Flags::A);
+        assert_eq!(Flags::from_bits_retain(0b10), Flags::B);
 
         assert_eq!(
-            unsafe { Flags::from_bits_unchecked(0b11) },
+            Flags::from_bits_retain(0b11),
             (Flags::A | Flags::B)
         );
         assert_eq!(
-            unsafe { Flags::from_bits_unchecked(0b1000) },
+            Flags::from_bits_retain(0b1000),
             (extra | Flags::empty())
         );
         assert_eq!(
-            unsafe { Flags::from_bits_unchecked(0b1001) },
+            Flags::from_bits_retain(0b1001),
             (extra | Flags::A)
         );
 
-        let extra = unsafe { EmptyFlags::from_bits_unchecked(0b1000) };
+        let extra = EmptyFlags::from_bits_retain(0b1000);
         assert_eq!(
-            unsafe { EmptyFlags::from_bits_unchecked(0b1000) },
+            EmptyFlags::from_bits_retain(0b1000),
             (extra | EmptyFlags::empty())
         );
     }
diff --git a/src/lib.rs b/src/lib.rs
--- a/src/lib.rs
+++ b/src/lib.rs
@@ -1157,7 +1357,7 @@ mod tests {
         assert!(!Flags::A.is_all());
         assert!(Flags::ABC.is_all());
 
-        let extra = unsafe { Flags::from_bits_unchecked(0b1000) };
+        let extra = Flags::from_bits_retain(0b1000);
         assert!(!extra.is_all());
         assert!(!(Flags::A | extra).is_all());
         assert!((Flags::ABC | extra).is_all());
diff --git a/src/lib.rs b/src/lib.rs
--- a/src/lib.rs
+++ b/src/lib.rs
@@ -1255,7 +1455,7 @@ mod tests {
 
     #[test]
     fn test_operators_unchecked() {
-        let extra = unsafe { Flags::from_bits_unchecked(0b1000) };
+        let extra = Flags::from_bits_retain(0b1000);
         let e1 = Flags::A | Flags::C | extra;
         let e2 = Flags::B | Flags::C;
         assert_eq!((e1 | e2), (Flags::ABC | extra)); // union
diff --git a/src/lib.rs b/src/lib.rs
--- a/src/lib.rs
+++ b/src/lib.rs
@@ -1274,9 +1474,9 @@ mod tests {
         let ab = Flags::A.union(Flags::B);
         let ac = Flags::A.union(Flags::C);
         let bc = Flags::B.union(Flags::C);
-        assert_eq!(ab.bits, 0b011);
-        assert_eq!(bc.bits, 0b110);
-        assert_eq!(ac.bits, 0b101);
+        assert_eq!(ab.bits(), 0b011);
+        assert_eq!(bc.bits(), 0b110);
+        assert_eq!(ac.bits(), 0b101);
 
         assert_eq!(ab, Flags::B.union(Flags::A));
         assert_eq!(ac, Flags::C.union(Flags::A));
diff --git a/src/lib.rs b/src/lib.rs
--- a/src/lib.rs
+++ b/src/lib.rs
@@ -1329,10 +1529,10 @@ mod tests {
 
     #[test]
     fn test_set_ops_unchecked() {
-        let extra = unsafe { Flags::from_bits_unchecked(0b1000) };
+        let extra = Flags::from_bits_retain(0b1000);
         let e1 = Flags::A.union(Flags::C).union(extra);
         let e2 = Flags::B.union(Flags::C);
-        assert_eq!(e1.bits, 0b1101);
+        assert_eq!(e1.bits(), 0b1101);
         assert_eq!(e1.union(e2), (Flags::ABC | extra));
         assert_eq!(e1.intersection(e2), Flags::C);
         assert_eq!(e1.difference(e2), Flags::A | extra);
diff --git a/src/lib.rs b/src/lib.rs
--- a/src/lib.rs
+++ b/src/lib.rs
@@ -1346,11 +1546,12 @@ mod tests {
     fn test_set_ops_exhaustive() {
         // Define a flag that contains gaps to help exercise edge-cases,
         // especially around "unknown" flags (e.g. ones outside of `all()`
-        // `from_bits_unchecked`).
+        // `from_bits_retain`).
         // - when lhs and rhs both have different sets of unknown flags.
         // - unknown flags at both ends, and in the middle
         // - cases with "gaps".
         bitflags! {
+            #[derive(Clone, Copy, Debug, PartialEq, Eq)]
             struct Test: u16 {
                 // Intentionally no `A`
                 const B = 0b000000010;
diff --git a/src/lib.rs b/src/lib.rs
--- a/src/lib.rs
+++ b/src/lib.rs
@@ -1364,12 +1565,12 @@ mod tests {
             }
         }
         let iter_test_flags =
-            || (0..=0b111_1111_1111).map(|bits| unsafe { Test::from_bits_unchecked(bits) });
+            || (0..=0b111_1111_1111).map(|bits| Test::from_bits_retain(bits));
 
         for a in iter_test_flags() {
             assert_eq!(
                 a.complement(),
-                Test::from_bits_truncate(!a.bits),
+                Test::from_bits_truncate(!a.bits()),
                 "wrong result: !({:?})",
                 a,
             );
diff --git a/src/lib.rs b/src/lib.rs
--- a/src/lib.rs
+++ b/src/lib.rs
@@ -1378,37 +1579,37 @@ mod tests {
                 // Check that the named operations produce the expected bitwise
                 // values.
                 assert_eq!(
-                    a.union(b).bits,
-                    a.bits | b.bits,
+                    a.union(b).bits(),
+                    a.bits() | b.bits(),
                     "wrong result: `{:?}` | `{:?}`",
                     a,
                     b,
                 );
                 assert_eq!(
-                    a.intersection(b).bits,
-                    a.bits & b.bits,
+                    a.intersection(b).bits(),
+                    a.bits() & b.bits(),
                     "wrong result: `{:?}` & `{:?}`",
                     a,
                     b,
                 );
                 assert_eq!(
-                    a.symmetric_difference(b).bits,
-                    a.bits ^ b.bits,
+                    a.symmetric_difference(b).bits(),
+                    a.bits() ^ b.bits(),
                     "wrong result: `{:?}` ^ `{:?}`",
                     a,
                     b,
                 );
                 assert_eq!(
-                    a.difference(b).bits,
-                    a.bits & !b.bits,
+                    a.difference(b).bits(),
+                    a.bits() & !b.bits(),
                     "wrong result: `{:?}` - `{:?}`",
                     a,
                     b,
                 );
                 // Note: Difference is checked as both `a - b` and `b - a`
                 assert_eq!(
-                    b.difference(a).bits,
-                    b.bits & !a.bits,
+                    b.difference(a).bits(),
+                    b.bits() & !a.bits(),
                     "wrong result: `{:?}` - `{:?}`",
                     b,
                     a,
diff --git a/src/lib.rs b/src/lib.rs
--- a/src/lib.rs
+++ b/src/lib.rs
@@ -1577,28 +1778,28 @@ mod tests {
 
     #[test]
     fn test_debug() {
-        assert_eq!(format!("{:?}", Flags::A | Flags::B), "A | B");
-        assert_eq!(format!("{:?}", Flags::empty()), "(empty)");
-        assert_eq!(format!("{:?}", Flags::ABC), "A | B | C");
+        assert_eq!(format!("{:?}", Flags::A | Flags::B), "Flags(A | B)");
+        assert_eq!(format!("{:?}", Flags::empty()), "Flags(empty)");
+        assert_eq!(format!("{:?}", Flags::ABC), "Flags(A | B | C)");
 
-        let extra = unsafe { Flags::from_bits_unchecked(0xb8) };
+        let extra = Flags::from_bits_retain(0xb8);
 
-        assert_eq!(format!("{:?}", extra), "0xb8");
-        assert_eq!(format!("{:?}", Flags::A | extra), "A | 0xb8");
+        assert_eq!(format!("{:?}", extra), "Flags(0xb8)");
+        assert_eq!(format!("{:?}", Flags::A | extra), "Flags(A | 0xb8)");
 
         assert_eq!(
             format!("{:?}", Flags::ABC | extra),
-            "A | B | C | ABC | 0xb8"
+            "Flags(A | B | C | ABC | 0xb8)"
         );
 
-        assert_eq!(format!("{:?}", EmptyFlags::empty()), "(empty)");
+        assert_eq!(format!("{:?}", EmptyFlags::empty()), "EmptyFlags(empty)");
     }
 
     #[test]
     fn test_binary() {
         assert_eq!(format!("{:b}", Flags::ABC), "111");
         assert_eq!(format!("{:#b}", Flags::ABC), "0b111");
-        let extra = unsafe { Flags::from_bits_unchecked(0b1010000) };
+        let extra = Flags::from_bits_retain(0b1010000);
         assert_eq!(format!("{:b}", Flags::ABC | extra), "1010111");
         assert_eq!(format!("{:#b}", Flags::ABC | extra), "0b1010111");
     }
diff --git a/src/lib.rs b/src/lib.rs
--- a/src/lib.rs
+++ b/src/lib.rs
@@ -1607,7 +1808,7 @@ mod tests {
     fn test_octal() {
         assert_eq!(format!("{:o}", LongFlags::LONG_A), "177777");
         assert_eq!(format!("{:#o}", LongFlags::LONG_A), "0o177777");
-        let extra = unsafe { LongFlags::from_bits_unchecked(0o5000000) };
+        let extra = LongFlags::from_bits_retain(0o5000000);
         assert_eq!(format!("{:o}", LongFlags::LONG_A | extra), "5177777");
         assert_eq!(format!("{:#o}", LongFlags::LONG_A | extra), "0o5177777");
     }
diff --git a/src/lib.rs b/src/lib.rs
--- a/src/lib.rs
+++ b/src/lib.rs
@@ -1616,7 +1817,7 @@ mod tests {
     fn test_lowerhex() {
         assert_eq!(format!("{:x}", LongFlags::LONG_A), "ffff");
         assert_eq!(format!("{:#x}", LongFlags::LONG_A), "0xffff");
-        let extra = unsafe { LongFlags::from_bits_unchecked(0xe00000) };
+        let extra = LongFlags::from_bits_retain(0xe00000);
         assert_eq!(format!("{:x}", LongFlags::LONG_A | extra), "e0ffff");
         assert_eq!(format!("{:#x}", LongFlags::LONG_A | extra), "0xe0ffff");
     }
diff --git a/src/lib.rs b/src/lib.rs
--- a/src/lib.rs
+++ b/src/lib.rs
@@ -1625,17 +1826,19 @@ mod tests {
     fn test_upperhex() {
         assert_eq!(format!("{:X}", LongFlags::LONG_A), "FFFF");
         assert_eq!(format!("{:#X}", LongFlags::LONG_A), "0xFFFF");
-        let extra = unsafe { LongFlags::from_bits_unchecked(0xe00000) };
+        let extra = LongFlags::from_bits_retain(0xe00000);
         assert_eq!(format!("{:X}", LongFlags::LONG_A | extra), "E0FFFF");
         assert_eq!(format!("{:#X}", LongFlags::LONG_A | extra), "0xE0FFFF");
     }
 
     mod submodule {
         bitflags! {
+            #[derive(Clone, Copy)]
             pub struct PublicFlags: i8 {
                 const X = 0;
             }
 
+            #[derive(Clone, Copy)]
             struct PrivateFlags: i8 {
                 const Y = 0;
             }
diff --git a/src/lib.rs b/src/lib.rs
--- a/src/lib.rs
+++ b/src/lib.rs
@@ -1659,6 +1862,7 @@ mod tests {
 
         bitflags! {
             /// baz
+            #[derive(Clone, Copy)]
             struct Flags: foo::Bar {
                 const A = 0b00000001;
                 #[cfg(foo)]
diff --git a/src/lib.rs b/src/lib.rs
--- a/src/lib.rs
+++ b/src/lib.rs
@@ -1672,19 +1876,21 @@ mod tests {
     #[test]
     fn test_in_function() {
         bitflags! {
-           struct Flags: u8 {
+            #[derive(Clone, Copy, Debug, PartialEq, Eq)]
+            struct Flags: u8 {
                 const A = 1;
                 #[cfg(any())] // false
                 const B = 2;
             }
         }
         assert_eq!(Flags::all(), Flags::A);
-        assert_eq!(format!("{:?}", Flags::A), "A");
+        assert_eq!(format!("{:?}", Flags::A), "Flags(A)");
     }
 
     #[test]
     fn test_deprecated() {
         bitflags! {
+            #[derive(Clone, Copy)]
             pub struct TestFlags: u32 {
                 #[deprecated(note = "Use something else.")]
                 const ONE = 1;
diff --git a/src/lib.rs b/src/lib.rs
--- a/src/lib.rs
+++ b/src/lib.rs
@@ -1696,6 +1902,7 @@ mod tests {
     fn test_pub_crate() {
         mod module {
             bitflags! {
+                #[derive(Clone, Copy)]
                 pub (crate) struct Test: u8 {
                     const FOO = 1;
                 }
diff --git a/src/lib.rs b/src/lib.rs
--- a/src/lib.rs
+++ b/src/lib.rs
@@ -1712,6 +1919,7 @@ mod tests {
                 bitflags! {
                     // `pub (in super)` means only the module `module` will
                     // be able to access this.
+                    #[derive(Clone, Copy)]
                     pub (in super) struct Test: u8 {
                         const FOO = 1;
                     }
diff --git a/src/lib.rs b/src/lib.rs
--- a/src/lib.rs
+++ b/src/lib.rs
@@ -1737,6 +1945,7 @@ mod tests {
     #[test]
     fn test_zero_value_flags() {
         bitflags! {
+            #[derive(Clone, Copy, Debug, PartialEq, Eq)]
             struct Flags: u32 {
                 const NONE = 0b0;
                 const SOME = 0b1;
diff --git a/src/lib.rs b/src/lib.rs
--- a/src/lib.rs
+++ b/src/lib.rs
@@ -1747,8 +1956,8 @@ mod tests {
         assert!(Flags::SOME.contains(Flags::NONE));
         assert!(Flags::NONE.is_empty());
 
-        assert_eq!(format!("{:?}", Flags::empty()), "(empty)");
-        assert_eq!(format!("{:?}", Flags::SOME), "NONE | SOME");
+        assert_eq!(format!("{:?}", Flags::empty()), "Flags(empty)");
+        assert_eq!(format!("{:?}", Flags::SOME), "Flags(NONE | SOME)");
     }
 
     #[test]
diff --git a/src/lib.rs b/src/lib.rs
--- a/src/lib.rs
+++ b/src/lib.rs
@@ -1759,69 +1968,33 @@ mod tests {
     #[test]
     fn test_u128_bitflags() {
         bitflags! {
-            struct Flags128: u128 {
+            #[derive(Clone, Copy, Debug, PartialEq, Eq)]
+            struct Flags: u128 {
                 const A = 0x0000_0000_0000_0000_0000_0000_0000_0001;
                 const B = 0x0000_0000_0000_1000_0000_0000_0000_0000;
                 const C = 0x8000_0000_0000_0000_0000_0000_0000_0000;
-                const ABC = Self::A.bits | Self::B.bits | Self::C.bits;
+                const ABC = Self::A.bits() | Self::B.bits() | Self::C.bits();
             }
         }
 
-        assert_eq!(Flags128::ABC, Flags128::A | Flags128::B | Flags128::C);
-        assert_eq!(Flags128::A.bits, 0x0000_0000_0000_0000_0000_0000_0000_0001);
-        assert_eq!(Flags128::B.bits, 0x0000_0000_0000_1000_0000_0000_0000_0000);
-        assert_eq!(Flags128::C.bits, 0x8000_0000_0000_0000_0000_0000_0000_0000);
+        assert_eq!(Flags::ABC, Flags::A | Flags::B | Flags::C);
+        assert_eq!(Flags::A.bits(), 0x0000_0000_0000_0000_0000_0000_0000_0001);
+        assert_eq!(Flags::B.bits(), 0x0000_0000_0000_1000_0000_0000_0000_0000);
+        assert_eq!(Flags::C.bits(), 0x8000_0000_0000_0000_0000_0000_0000_0000);
         assert_eq!(
-            Flags128::ABC.bits,
+            Flags::ABC.bits(),
             0x8000_0000_0000_1000_0000_0000_0000_0001
         );
-        assert_eq!(format!("{:?}", Flags128::A), "A");
-        assert_eq!(format!("{:?}", Flags128::B), "B");
-        assert_eq!(format!("{:?}", Flags128::C), "C");
-        assert_eq!(format!("{:?}", Flags128::ABC), "A | B | C");
-    }
-
-    #[test]
-    fn test_serde_bitflags_serialize() {
-        let flags = SerdeFlags::A | SerdeFlags::B;
-
-        let serialized = serde_json::to_string(&flags).unwrap();
-
-        assert_eq!(serialized, r#"{"bits":3}"#);
-    }
-
-    #[test]
-    fn test_serde_bitflags_deserialize() {
-        let deserialized: SerdeFlags = serde_json::from_str(r#"{"bits":12}"#).unwrap();
-
-        let expected = SerdeFlags::C | SerdeFlags::D;
-
-        assert_eq!(deserialized.bits, expected.bits);
-    }
-
-    #[test]
-    fn test_serde_bitflags_roundtrip() {
-        let flags = SerdeFlags::A | SerdeFlags::B;
-
-        let deserialized: SerdeFlags =
-            serde_json::from_str(&serde_json::to_string(&flags).unwrap()).unwrap();
-
-        assert_eq!(deserialized.bits, flags.bits);
-    }
-
-    bitflags! {
-        #[derive(serde_derive::Serialize, serde_derive::Deserialize)]
-        struct SerdeFlags: u32 {
-            const A = 1;
-            const B = 2;
-            const C = 4;
-            const D = 8;
-        }
+        assert_eq!(format!("{:?}", Flags::A), "Flags(A)");
+        assert_eq!(format!("{:?}", Flags::B), "Flags(B)");
+        assert_eq!(format!("{:?}", Flags::C), "Flags(C)");
+        assert_eq!(format!("{:?}", Flags::ABC), "Flags(A | B | C)");
     }
 
     #[test]
     fn test_from_bits_edge_cases() {
         bitflags! {
+            #[derive(Clone, Copy, Debug, PartialEq, Eq)]
             struct Flags: u8 {
                 const A = 0b00000001;
                 const BC = 0b00000110;
diff --git a/src/lib.rs b/src/lib.rs
--- a/src/lib.rs
+++ b/src/lib.rs
@@ -1837,6 +2010,7 @@ mod tests {
     #[test]
     fn test_from_bits_truncate_edge_cases() {
         bitflags! {
+            #[derive(Clone, Copy, Debug, PartialEq, Eq)]
             struct Flags: u8 {
                 const A = 0b00000001;
                 const BC = 0b00000110;
diff --git a/src/lib.rs b/src/lib.rs
--- a/src/lib.rs
+++ b/src/lib.rs
@@ -1852,6 +2026,7 @@ mod tests {
     #[test]
     fn test_iter() {
         bitflags! {
+            #[derive(Clone, Copy, Debug, PartialEq, Eq)]
             struct Flags: u32 {
                 const ONE  = 0b001;
                 const TWO  = 0b010;
diff --git /dev/null b/src/serde_support.rs
new file mode 100644
--- /dev/null
+++ b/src/serde_support.rs
@@ -0,0 +1,84 @@
+use core::fmt;
+use serde::{Serializer, Deserializer, Serialize, Deserialize, ser::SerializeStruct, de::{Error, MapAccess, Visitor}};
+
+// These methods are compatible with the result of `#[derive(Serialize, Deserialize)]` on bitflags `1.0` types
+
+pub fn serialize_bits_default<B: Serialize, S: Serializer>(name: &'static str, bits: &B, serializer: S) -> Result<S::Ok, S::Error> {
+    let mut serialize_struct = serializer.serialize_struct(name, 1)?;
+    serialize_struct.serialize_field("bits", bits)?;
+    serialize_struct.end()
+}
+
+pub fn deserialize_bits_default<'de, B: Deserialize<'de>, D: Deserializer<'de>>(name: &'static str, deserializer: D) -> Result<B, D::Error> {
+    struct BitsVisitor<T>(core::marker::PhantomData<T>);
+
+    impl<'de, T: Deserialize<'de>> Visitor<'de> for BitsVisitor<T> {
+        type Value = T;
+
+        fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
+            formatter.write_str("a primitive bitflags value wrapped in a struct")
+        }
+
+        fn visit_map<A: MapAccess<'de>>(self, mut map: A) -> Result<Self::Value, A::Error> {
+            let mut bits = None;
+
+            while let Some(key) = map.next_key()? {
+                match key {
+                    "bits" => {
+                        if bits.is_some() {
+                            return Err(Error::duplicate_field("bits"));
+                        }
+
+                        bits = Some(map.next_value()?);
+                    }
+                    v => return Err(Error::unknown_field(v, &["bits"]))
+                }
+            }
+
+            bits.ok_or_else(|| Error::missing_field("bits"))
+        }
+    }
+
+    deserializer.deserialize_struct(name, &["bits"], BitsVisitor(Default::default()))
+}
+
+#[cfg(test)]
+mod tests {
+    bitflags! {
+        #[derive(serde_derive::Serialize, serde_derive::Deserialize)]
+        struct SerdeFlags: u32 {
+            const A = 1;
+            const B = 2;
+            const C = 4;
+            const D = 8;
+        }
+    }
+
+    #[test]
+    fn test_serde_bitflags_default_serialize() {
+        let flags = SerdeFlags::A | SerdeFlags::B;
+
+        let serialized = serde_json::to_string(&flags).unwrap();
+
+        assert_eq!(serialized, r#"{"bits":3}"#);
+    }
+
+    #[test]
+    fn test_serde_bitflags_default_deserialize() {
+        let deserialized: SerdeFlags = serde_json::from_str(r#"{"bits":12}"#).unwrap();
+
+        let expected = SerdeFlags::C | SerdeFlags::D;
+
+        assert_eq!(deserialized.bits(), expected.bits());
+    }
+
+    #[test]
+    fn test_serde_bitflags_default_roundtrip() {
+        let flags = SerdeFlags::A | SerdeFlags::B;
+
+        let deserialized: SerdeFlags =
+            serde_json::from_str(&serde_json::to_string(&flags).unwrap()).unwrap();
+
+        assert_eq!(deserialized.bits(), flags.bits());
+    }
+}
\ No newline at end of file
diff --git a/tests/basic.rs b/tests/basic.rs
--- a/tests/basic.rs
+++ b/tests/basic.rs
@@ -4,13 +4,14 @@ use bitflags::bitflags;
 
 bitflags! {
     /// baz
+    #[derive(Debug, PartialEq, Eq)]
     struct Flags: u32 {
         const A = 0b00000001;
         #[doc = "bar"]
         const B = 0b00000010;
         const C = 0b00000100;
         #[doc = "foo"]
-        const ABC = Flags::A.bits | Flags::B.bits | Flags::C.bits;
+        const ABC = Flags::A.bits() | Flags::B.bits() | Flags::C.bits();
     }
 }
 
diff --git a/tests/compile-fail/impls/copy.stderr /dev/null
--- a/tests/compile-fail/impls/copy.stderr
+++ /dev/null
@@ -1,27 +0,0 @@
-error[E0119]: conflicting implementations of trait `std::marker::Copy` for type `Flags`
- --> $DIR/copy.rs:3:1
-  |
-3 | / bitflags! {
-4 | |     #[derive(Clone, Copy)]
-  | |                     ---- first implementation here
-5 | |     struct Flags: u32 {
-6 | |         const A = 0b00000001;
-7 | |     }
-8 | | }
-  | |_^ conflicting implementation for `Flags`
-  |
-  = note: this error originates in the derive macro `Copy` (in Nightly builds, run with -Z macro-backtrace for more info)
-
-error[E0119]: conflicting implementations of trait `std::clone::Clone` for type `Flags`
- --> $DIR/copy.rs:3:1
-  |
-3 | / bitflags! {
-4 | |     #[derive(Clone, Copy)]
-  | |              ----- first implementation here
-5 | |     struct Flags: u32 {
-6 | |         const A = 0b00000001;
-7 | |     }
-8 | | }
-  | |_^ conflicting implementation for `Flags`
-  |
-  = note: this error originates in the derive macro `Clone` (in Nightly builds, run with -Z macro-backtrace for more info)
diff --git a/tests/compile-fail/impls/eq.stderr /dev/null
--- a/tests/compile-fail/impls/eq.stderr
+++ /dev/null
@@ -1,55 +0,0 @@
-error[E0119]: conflicting implementations of trait `std::marker::StructuralPartialEq` for type `Flags`
- --> $DIR/eq.rs:3:1
-  |
-3 | / bitflags! {
-4 | |     #[derive(PartialEq, Eq)]
-  | |              --------- first implementation here
-5 | |     struct Flags: u32 {
-6 | |         const A = 0b00000001;
-7 | |     }
-8 | | }
-  | |_^ conflicting implementation for `Flags`
-  |
-  = note: this error originates in the derive macro `PartialEq` (in Nightly builds, run with -Z macro-backtrace for more info)
-
-error[E0119]: conflicting implementations of trait `std::cmp::PartialEq` for type `Flags`
- --> $DIR/eq.rs:3:1
-  |
-3 | / bitflags! {
-4 | |     #[derive(PartialEq, Eq)]
-  | |              --------- first implementation here
-5 | |     struct Flags: u32 {
-6 | |         const A = 0b00000001;
-7 | |     }
-8 | | }
-  | |_^ conflicting implementation for `Flags`
-  |
-  = note: this error originates in the derive macro `PartialEq` (in Nightly builds, run with -Z macro-backtrace for more info)
-
-error[E0119]: conflicting implementations of trait `std::marker::StructuralEq` for type `Flags`
- --> $DIR/eq.rs:3:1
-  |
-3 | / bitflags! {
-4 | |     #[derive(PartialEq, Eq)]
-  | |                         -- first implementation here
-5 | |     struct Flags: u32 {
-6 | |         const A = 0b00000001;
-7 | |     }
-8 | | }
-  | |_^ conflicting implementation for `Flags`
-  |
-  = note: this error originates in the derive macro `Eq` (in Nightly builds, run with -Z macro-backtrace for more info)
-
-error[E0119]: conflicting implementations of trait `std::cmp::Eq` for type `Flags`
- --> $DIR/eq.rs:3:1
-  |
-3 | / bitflags! {
-4 | |     #[derive(PartialEq, Eq)]
-  | |                         -- first implementation here
-5 | |     struct Flags: u32 {
-6 | |         const A = 0b00000001;
-7 | |     }
-8 | | }
-  | |_^ conflicting implementation for `Flags`
-  |
-  = note: this error originates in the derive macro `Eq` (in Nightly builds, run with -Z macro-backtrace for more info)
diff --git a/tests/compile-fail/non_integer_base/all_defined.stderr b/tests/compile-fail/non_integer_base/all_defined.stderr
--- a/tests/compile-fail/non_integer_base/all_defined.stderr
+++ b/tests/compile-fail/non_integer_base/all_defined.stderr
@@ -4,6 +4,16 @@ error[E0277]: the trait bound `MyInt: Bits` is not satisfied
 116 |     struct Flags128: MyInt {
     |                      ^^^^^ the trait `Bits` is not implemented for `MyInt`
     |
+    = help: the following other types implement trait `Bits`:
+              i128
+              i16
+              i32
+              i64
+              i8
+              u128
+              u16
+              u32
+            and 2 others
 note: required by a bound in `bitflags::BitFlags::Bits`
    --> src/bitflags_trait.rs
     |
diff --git a/tests/compile-fail/non_integer_base/all_defined.stderr b/tests/compile-fail/non_integer_base/all_defined.stderr
--- a/tests/compile-fail/non_integer_base/all_defined.stderr
+++ b/tests/compile-fail/non_integer_base/all_defined.stderr
@@ -22,7 +32,17 @@ error[E0277]: the trait bound `MyInt: Bits` is not satisfied
 121 | | }
     | |_^ the trait `Bits` is not implemented for `MyInt`
     |
-    = note: this error originates in the macro `__impl_bitflags` (in Nightly builds, run with -Z macro-backtrace for more info)
+    = help: the following other types implement trait `Bits`:
+              i128
+              i16
+              i32
+              i64
+              i8
+              u128
+              u16
+              u32
+            and 2 others
+    = note: this error originates in the macro `__impl_internal_bitflags` which comes from the expansion of the macro `bitflags` (in Nightly builds, run with -Z macro-backtrace for more info)
 
 error[E0277]: the trait bound `MyInt: Bits` is not satisfied
    --> tests/compile-fail/non_integer_base/all_defined.rs:115:1
diff --git a/tests/compile-fail/non_integer_base/all_defined.stderr b/tests/compile-fail/non_integer_base/all_defined.stderr
--- a/tests/compile-fail/non_integer_base/all_defined.stderr
+++ b/tests/compile-fail/non_integer_base/all_defined.stderr
@@ -36,7 +56,17 @@ error[E0277]: the trait bound `MyInt: Bits` is not satisfied
 121 | | }
     | |_^ the trait `Bits` is not implemented for `MyInt`
     |
-    = note: this error originates in the macro `__impl_bitflags` (in Nightly builds, run with -Z macro-backtrace for more info)
+    = help: the following other types implement trait `Bits`:
+              i128
+              i16
+              i32
+              i64
+              i8
+              u128
+              u16
+              u32
+            and 2 others
+    = note: this error originates in the macro `__impl_internal_bitflags` which comes from the expansion of the macro `bitflags` (in Nightly builds, run with -Z macro-backtrace for more info)
 
 error[E0277]: the trait bound `MyInt: Bits` is not satisfied
    --> tests/compile-fail/non_integer_base/all_defined.rs:115:1
diff --git a/tests/compile-fail/non_integer_base/all_defined.stderr b/tests/compile-fail/non_integer_base/all_defined.stderr
--- a/tests/compile-fail/non_integer_base/all_defined.stderr
+++ b/tests/compile-fail/non_integer_base/all_defined.stderr
@@ -50,7 +80,69 @@ error[E0277]: the trait bound `MyInt: Bits` is not satisfied
 121 | | }
     | |_^ the trait `Bits` is not implemented for `MyInt`
     |
-    = note: this error originates in the macro `__impl_bitflags` (in Nightly builds, run with -Z macro-backtrace for more info)
+    = help: the following other types implement trait `Bits`:
+              i128
+              i16
+              i32
+              i64
+              i8
+              u128
+              u16
+              u32
+            and 2 others
+    = note: this error originates in the macro `__impl_internal_bitflags` which comes from the expansion of the macro `bitflags` (in Nightly builds, run with -Z macro-backtrace for more info)
+
+error[E0277]: can't compare `MyInt` with `_` in const contexts
+   --> tests/compile-fail/non_integer_base/all_defined.rs:115:1
+    |
+115 | / bitflags! {
+116 | |     struct Flags128: MyInt {
+117 | |         const A = MyInt(0b0000_0001u8);
+118 | |         const B = MyInt(0b0000_0010u8);
+119 | |         const C = MyInt(0b0000_0100u8);
+120 | |     }
+121 | | }
+    | |_^ no implementation for `MyInt == _`
+    |
+    = help: the trait `~const PartialEq<_>` is not implemented for `MyInt`
+note: the trait `PartialEq<_>` is implemented for `MyInt`, but that implementation is not `const`
+   --> tests/compile-fail/non_integer_base/all_defined.rs:115:1
+    |
+115 | / bitflags! {
+116 | |     struct Flags128: MyInt {
+117 | |         const A = MyInt(0b0000_0001u8);
+118 | |         const B = MyInt(0b0000_0010u8);
+119 | |         const C = MyInt(0b0000_0100u8);
+120 | |     }
+121 | | }
+    | |_^
+    = note: this error originates in the macro `__impl_internal_bitflags` which comes from the expansion of the macro `bitflags` (in Nightly builds, run with -Z macro-backtrace for more info)
+
+error[E0277]: can't compare `MyInt` with `_` in const contexts
+   --> tests/compile-fail/non_integer_base/all_defined.rs:115:1
+    |
+115 | / bitflags! {
+116 | |     struct Flags128: MyInt {
+117 | |         const A = MyInt(0b0000_0001u8);
+118 | |         const B = MyInt(0b0000_0010u8);
+119 | |         const C = MyInt(0b0000_0100u8);
+120 | |     }
+121 | | }
+    | |_^ no implementation for `MyInt == _`
+    |
+    = help: the trait `~const PartialEq<_>` is not implemented for `MyInt`
+note: the trait `PartialEq<_>` is implemented for `MyInt`, but that implementation is not `const`
+   --> tests/compile-fail/non_integer_base/all_defined.rs:115:1
+    |
+115 | / bitflags! {
+116 | |     struct Flags128: MyInt {
+117 | |         const A = MyInt(0b0000_0001u8);
+118 | |         const B = MyInt(0b0000_0010u8);
+119 | |         const C = MyInt(0b0000_0100u8);
+120 | |     }
+121 | | }
+    | |_^
+    = note: this error originates in the macro `__impl_internal_bitflags` which comes from the expansion of the macro `bitflags` (in Nightly builds, run with -Z macro-backtrace for more info)
 
 error[E0277]: the trait bound `MyInt: Bits` is not satisfied
    --> tests/compile-fail/non_integer_base/all_defined.rs:115:1
diff --git a/tests/compile-fail/non_integer_base/all_defined.stderr b/tests/compile-fail/non_integer_base/all_defined.stderr
--- a/tests/compile-fail/non_integer_base/all_defined.stderr
+++ b/tests/compile-fail/non_integer_base/all_defined.stderr
@@ -64,4 +156,142 @@ error[E0277]: the trait bound `MyInt: Bits` is not satisfied
 121 | | }
     | |_^ the trait `Bits` is not implemented for `MyInt`
     |
-    = note: this error originates in the macro `__impl_bitflags` (in Nightly builds, run with -Z macro-backtrace for more info)
+    = help: the following other types implement trait `Bits`:
+              i128
+              i16
+              i32
+              i64
+              i8
+              u128
+              u16
+              u32
+            and 2 others
+    = note: this error originates in the macro `__impl_internal_bitflags` which comes from the expansion of the macro `bitflags` (in Nightly builds, run with -Z macro-backtrace for more info)
+
+error[E0277]: the trait bound `MyInt: Bits` is not satisfied
+   --> tests/compile-fail/non_integer_base/all_defined.rs:115:1
+    |
+115 | / bitflags! {
+116 | |     struct Flags128: MyInt {
+117 | |         const A = MyInt(0b0000_0001u8);
+118 | |         const B = MyInt(0b0000_0010u8);
+119 | |         const C = MyInt(0b0000_0100u8);
+120 | |     }
+121 | | }
+    | |_^ the trait `Bits` is not implemented for `MyInt`
+    |
+    = help: the following other types implement trait `Bits`:
+              i128
+              i16
+              i32
+              i64
+              i8
+              u128
+              u16
+              u32
+            and 2 others
+    = note: this error originates in the macro `__impl_internal_bitflags` which comes from the expansion of the macro `bitflags` (in Nightly builds, run with -Z macro-backtrace for more info)
+
+error[E0277]: can't compare `MyInt` with `_` in const contexts
+   --> tests/compile-fail/non_integer_base/all_defined.rs:115:1
+    |
+115 | / bitflags! {
+116 | |     struct Flags128: MyInt {
+117 | |         const A = MyInt(0b0000_0001u8);
+118 | |         const B = MyInt(0b0000_0010u8);
+119 | |         const C = MyInt(0b0000_0100u8);
+120 | |     }
+121 | | }
+    | |_^ no implementation for `MyInt == _`
+    |
+    = help: the trait `~const PartialEq<_>` is not implemented for `MyInt`
+note: the trait `PartialEq<_>` is implemented for `MyInt`, but that implementation is not `const`
+   --> tests/compile-fail/non_integer_base/all_defined.rs:115:1
+    |
+115 | / bitflags! {
+116 | |     struct Flags128: MyInt {
+117 | |         const A = MyInt(0b0000_0001u8);
+118 | |         const B = MyInt(0b0000_0010u8);
+119 | |         const C = MyInt(0b0000_0100u8);
+120 | |     }
+121 | | }
+    | |_^
+    = note: this error originates in the macro `__impl_internal_bitflags` which comes from the expansion of the macro `bitflags` (in Nightly builds, run with -Z macro-backtrace for more info)
+
+error[E0277]: can't compare `MyInt` with `_` in const contexts
+   --> tests/compile-fail/non_integer_base/all_defined.rs:115:1
+    |
+115 | / bitflags! {
+116 | |     struct Flags128: MyInt {
+117 | |         const A = MyInt(0b0000_0001u8);
+118 | |         const B = MyInt(0b0000_0010u8);
+119 | |         const C = MyInt(0b0000_0100u8);
+120 | |     }
+121 | | }
+    | |_^ no implementation for `MyInt == _`
+    |
+    = help: the trait `~const PartialEq<_>` is not implemented for `MyInt`
+note: the trait `PartialEq<_>` is implemented for `MyInt`, but that implementation is not `const`
+   --> tests/compile-fail/non_integer_base/all_defined.rs:115:1
+    |
+115 | / bitflags! {
+116 | |     struct Flags128: MyInt {
+117 | |         const A = MyInt(0b0000_0001u8);
+118 | |         const B = MyInt(0b0000_0010u8);
+119 | |         const C = MyInt(0b0000_0100u8);
+120 | |     }
+121 | | }
+    | |_^
+    = note: this error originates in the macro `__impl_internal_bitflags` which comes from the expansion of the macro `bitflags` (in Nightly builds, run with -Z macro-backtrace for more info)
+
+error[E0277]: can't compare `MyInt` with `_` in const contexts
+   --> tests/compile-fail/non_integer_base/all_defined.rs:115:1
+    |
+115 | / bitflags! {
+116 | |     struct Flags128: MyInt {
+117 | |         const A = MyInt(0b0000_0001u8);
+118 | |         const B = MyInt(0b0000_0010u8);
+119 | |         const C = MyInt(0b0000_0100u8);
+120 | |     }
+121 | | }
+    | |_^ no implementation for `MyInt == _`
+    |
+    = help: the trait `~const PartialEq<_>` is not implemented for `MyInt`
+note: the trait `PartialEq<_>` is implemented for `MyInt`, but that implementation is not `const`
+   --> tests/compile-fail/non_integer_base/all_defined.rs:115:1
+    |
+115 | / bitflags! {
+116 | |     struct Flags128: MyInt {
+117 | |         const A = MyInt(0b0000_0001u8);
+118 | |         const B = MyInt(0b0000_0010u8);
+119 | |         const C = MyInt(0b0000_0100u8);
+120 | |     }
+121 | | }
+    | |_^
+    = note: this error originates in the macro `__impl_internal_bitflags` which comes from the expansion of the macro `bitflags` (in Nightly builds, run with -Z macro-backtrace for more info)
+
+error[E0277]: can't compare `MyInt` with `_` in const contexts
+   --> tests/compile-fail/non_integer_base/all_defined.rs:115:1
+    |
+115 | / bitflags! {
+116 | |     struct Flags128: MyInt {
+117 | |         const A = MyInt(0b0000_0001u8);
+118 | |         const B = MyInt(0b0000_0010u8);
+119 | |         const C = MyInt(0b0000_0100u8);
+120 | |     }
+121 | | }
+    | |_^ no implementation for `MyInt == _`
+    |
+    = help: the trait `~const PartialEq<_>` is not implemented for `MyInt`
+note: the trait `PartialEq<_>` is implemented for `MyInt`, but that implementation is not `const`
+   --> tests/compile-fail/non_integer_base/all_defined.rs:115:1
+    |
+115 | / bitflags! {
+116 | |     struct Flags128: MyInt {
+117 | |         const A = MyInt(0b0000_0001u8);
+118 | |         const B = MyInt(0b0000_0010u8);
+119 | |         const C = MyInt(0b0000_0100u8);
+120 | |     }
+121 | | }
+    | |_^
+    = note: this error originates in the macro `__impl_internal_bitflags` which comes from the expansion of the macro `bitflags` (in Nightly builds, run with -Z macro-backtrace for more info)
diff --git a/tests/compile-fail/non_integer_base/all_missing.stderr b/tests/compile-fail/non_integer_base/all_missing.stderr
--- a/tests/compile-fail/non_integer_base/all_missing.stderr
+++ b/tests/compile-fail/non_integer_base/all_missing.stderr
@@ -1,5 +1,5 @@
 error[E0204]: the trait `Copy` may not be implemented for this type
-  --> $DIR/all_missing.rs:5:1
+  --> tests/compile-fail/non_integer_base/all_missing.rs:5:1
    |
 5  | / bitflags! {
 6  | |     struct Flags128: MyInt {
diff --git a/tests/compile-fail/non_integer_base/all_missing.stderr b/tests/compile-fail/non_integer_base/all_missing.stderr
--- a/tests/compile-fail/non_integer_base/all_missing.stderr
+++ b/tests/compile-fail/non_integer_base/all_missing.stderr
@@ -10,4 +10,4 @@ error[E0204]: the trait `Copy` may not be implemented for this type
 11 | | }
    | |_^ this field does not implement `Copy`
    |
-   = note: this error originates in the derive macro `Copy` (in Nightly builds, run with -Z macro-backtrace for more info)
+   = note: this error originates in the derive macro `Copy` which comes from the expansion of the macro `bitflags` (in Nightly builds, run with -Z macro-backtrace for more info)
diff --git /dev/null b/tests/compile-fail/redefined.rs
new file mode 100644
--- /dev/null
+++ b/tests/compile-fail/redefined.rs
@@ -0,0 +1,14 @@
+#[macro_use]
+extern crate bitflags;
+
+bitflags! {
+    pub struct Flags1 {
+        const A = 1;
+    }
+}
+
+bitflags! {
+    pub struct Flags1 {
+        const A = 1;
+    }
+}
diff --git /dev/null b/tests/compile-fail/redefined.stderr
new file mode 100644
--- /dev/null
+++ b/tests/compile-fail/redefined.stderr
@@ -0,0 +1,17 @@
+error: no rules expected the token `{`
+ --> tests/compile-fail/redefined.rs:5:23
+  |
+5 |     pub struct Flags1 {
+  |                       ^ no rules expected this token in macro call
+
+error: no rules expected the token `{`
+  --> tests/compile-fail/redefined.rs:11:23
+   |
+11 |     pub struct Flags1 {
+   |                       ^ no rules expected this token in macro call
+
+error[E0601]: `main` function not found in crate `$CRATE`
+  --> tests/compile-fail/redefined.rs:14:2
+   |
+14 | }
+   |  ^ consider adding a `main` function to `$DIR/tests/compile-fail/redefined.rs`
diff --git /dev/null b/tests/compile-fail/syntax/missing_type.rs
new file mode 100644
--- /dev/null
+++ b/tests/compile-fail/syntax/missing_type.rs
@@ -0,0 +1,8 @@
+#[macro_use]
+extern crate bitflags;
+
+bitflags! {
+    pub struct Flags1 {
+        const A = 1;
+    }
+}
diff --git /dev/null b/tests/compile-fail/syntax/missing_type.stderr
new file mode 100644
--- /dev/null
+++ b/tests/compile-fail/syntax/missing_type.stderr
@@ -0,0 +1,11 @@
+error: no rules expected the token `{`
+ --> tests/compile-fail/syntax/missing_type.rs:5:23
+  |
+5 |     pub struct Flags1 {
+  |                       ^ no rules expected this token in macro call
+
+error[E0601]: `main` function not found in crate `$CRATE`
+ --> tests/compile-fail/syntax/missing_type.rs:8:2
+  |
+8 | }
+  |  ^ consider adding a `main` function to `$DIR/tests/compile-fail/syntax/missing_type.rs`
diff --git /dev/null b/tests/compile-fail/syntax/missing_value.rs
new file mode 100644
--- /dev/null
+++ b/tests/compile-fail/syntax/missing_value.rs
@@ -0,0 +1,8 @@
+#[macro_use]
+extern crate bitflags;
+
+bitflags! {
+    pub struct Flags1 {
+        const A;
+    }
+}
diff --git /dev/null b/tests/compile-fail/syntax/missing_value.stderr
new file mode 100644
--- /dev/null
+++ b/tests/compile-fail/syntax/missing_value.stderr
@@ -0,0 +1,11 @@
+error: no rules expected the token `{`
+ --> tests/compile-fail/syntax/missing_value.rs:5:23
+  |
+5 |     pub struct Flags1 {
+  |                       ^ no rules expected this token in macro call
+
+error[E0601]: `main` function not found in crate `$CRATE`
+ --> tests/compile-fail/syntax/missing_value.rs:8:2
+  |
+8 | }
+  |  ^ consider adding a `main` function to `$DIR/tests/compile-fail/syntax/missing_value.rs`
diff --git a/tests/compile-fail/trait/custom_impl.rs b/tests/compile-fail/trait/custom_impl.rs
--- a/tests/compile-fail/trait/custom_impl.rs
+++ b/tests/compile-fail/trait/custom_impl.rs
@@ -25,7 +25,7 @@ impl BitFlags for BootlegFlags {
         unimplemented!()
     }
 
-    unsafe fn from_bits_unchecked(_: u32) -> BootlegFlags {
+    fn from_bits_retain(_: u32) -> BootlegFlags {
         unimplemented!()
     }
 
diff --git a/tests/compile-fail/visibility/private_field.rs /dev/null
--- a/tests/compile-fail/visibility/private_field.rs
+++ /dev/null
@@ -1,13 +0,0 @@
-mod example {
-    use bitflags::bitflags;
-
-    bitflags! {
-        pub struct Flags1: u32 {
-            const FLAG_A = 0b00000001;
-        }
-    }
-}
-
-fn main() {
-    let flag1 = example::Flags1::FLAG_A.bits;
-}
diff --git a/tests/compile-fail/visibility/private_field.stderr /dev/null
--- a/tests/compile-fail/visibility/private_field.stderr
+++ /dev/null
@@ -1,10 +0,0 @@
-error[E0616]: field `bits` of struct `Flags1` is private
-  --> $DIR/private_field.rs:12:41
-   |
-12 |     let flag1 = example::Flags1::FLAG_A.bits;
-   |                                         ^^^^ private field
-   |
-help: a method `bits` also exists, call it with parentheses
-   |
-12 |     let flag1 = example::Flags1::FLAG_A.bits();
-   |                                             ++
diff --git a/tests/compile-fail/visibility/private_flags.rs b/tests/compile-fail/visibility/private_flags.rs
--- a/tests/compile-fail/visibility/private_flags.rs
+++ b/tests/compile-fail/visibility/private_flags.rs
@@ -13,6 +13,6 @@ mod example {
 }
 
 fn main() {
-    let flag1 = example::Flags1::FLAG_A;
-    let flag2 = example::Flags2::FLAG_B;
+    let _ = example::Flags1::FLAG_A;
+    let _ = example::Flags2::FLAG_B;
 }
diff --git a/tests/compile-fail/visibility/private_flags.stderr b/tests/compile-fail/visibility/private_flags.stderr
--- a/tests/compile-fail/visibility/private_flags.stderr
+++ b/tests/compile-fail/visibility/private_flags.stderr
@@ -1,11 +1,11 @@
 error[E0603]: struct `Flags2` is private
-  --> $DIR/private_flags.rs:17:26
+  --> tests/compile-fail/visibility/private_flags.rs:17:22
    |
-17 |     let flag2 = example::Flags2::FLAG_B;
-   |                          ^^^^^^ private struct
+17 |     let _ = example::Flags2::FLAG_B;
+   |                      ^^^^^^ private struct
    |
 note: the struct `Flags2` is defined here
-  --> $DIR/private_flags.rs:4:5
+  --> tests/compile-fail/visibility/private_flags.rs:4:5
    |
 4  | /     bitflags! {
 5  | |         pub struct Flags1: u32 {
diff --git a/tests/compile-pass/impls/fmt.rs b/tests/compile-pass/impls/fmt.rs
--- a/tests/compile-pass/impls/fmt.rs
+++ b/tests/compile-pass/impls/fmt.rs
@@ -1,6 +1,7 @@
 use bitflags::bitflags;
 
 bitflags! {
+    #[derive(Debug)]
     struct Flags: u8 {
         const TWO = 0x2;
     }
diff --git a/tests/compile-pass/impls/fmt.rs b/tests/compile-pass/impls/fmt.rs
--- a/tests/compile-pass/impls/fmt.rs
+++ b/tests/compile-pass/impls/fmt.rs
@@ -8,7 +9,7 @@ bitflags! {
 
 fn main() {
     // bug #267 (https://github.com/bitflags/bitflags/issues/267)
-    let flags = unsafe { Flags::from_bits_unchecked(0b11) };
-    assert_eq!(format!("{:?}", flags), "TWO | 0x1");
-    assert_eq!(format!("{:#?}", flags), "TWO | 0x1");
+    let flags = Flags::from_bits_retain(0b11);
+    assert_eq!(format!("{:?}", flags), "Flags(TWO | 0x1)");
+    assert_eq!(format!("{:#?}", flags), "Flags(\n    TWO | 0x1,\n)");
 }
diff --git /dev/null b/tests/compile-pass/item_positions.rs
new file mode 100644
--- /dev/null
+++ b/tests/compile-pass/item_positions.rs
@@ -0,0 +1,52 @@
+#[macro_use]
+extern crate bitflags;
+
+bitflags! {
+    pub struct Flags1: u32 {
+        const A = 1;
+    }
+}
+
+bitflags! {
+    pub struct Flags2: u32 {
+        const A = 1;
+    }
+}
+
+pub mod nested {
+    bitflags! {
+        pub struct Flags1: u32 {
+            const A = 1;
+        }
+    }
+
+    bitflags! {
+        pub struct Flags2: u32 {
+            const A = 1;
+        }
+    }
+}
+
+pub const _: () = {
+    bitflags! {
+        pub struct Flags1: u32 {
+            const A = 1;
+        }
+    }
+};
+
+fn main() {
+    bitflags! {
+        pub struct Flags1: u32 {
+            const A = 1;
+        }
+    }
+
+    let _ = {
+        bitflags! {
+            pub struct Flags2: u32 {
+                const A = 1;
+            }
+        }
+    };
+}
diff --git a/tests/compile-pass/no_prelude.rs b/tests/compile-pass/no_prelude.rs
--- a/tests/compile-pass/no_prelude.rs
+++ b/tests/compile-pass/no_prelude.rs
@@ -7,7 +7,7 @@ bitflags::bitflags! {
         const A = 0b00000001;
         const B = 0b00000010;
         const C = 0b00000100;
-        const ABC = Flags::A.bits | Flags::B.bits | Flags::C.bits;
+        const ABC = Flags::A.bits() | Flags::B.bits() | Flags::C.bits();
     }
 }
 
diff --git a/tests/compile-pass/redefinition/macros.rs b/tests/compile-pass/redefinition/macros.rs
--- a/tests/compile-pass/redefinition/macros.rs
+++ b/tests/compile-pass/redefinition/macros.rs
@@ -13,6 +13,7 @@ macro_rules! write {
 }
 
 bitflags! {
+    #[derive(Debug)]
     struct Test: u8 {
         const A = 1;
     }
diff --git a/tests/compile-pass/redefinition/macros.rs b/tests/compile-pass/redefinition/macros.rs
--- a/tests/compile-pass/redefinition/macros.rs
+++ b/tests/compile-pass/redefinition/macros.rs
@@ -20,5 +21,5 @@ bitflags! {
 
 fn main() {
     // Just make sure we don't call the redefined `stringify` or `write` macro
-    assert_eq!(format!("{:?}", unsafe { Test::from_bits_unchecked(0b11) }), "A | 0x2");
+    assert_eq!(format!("{:?}", Test::from_bits_retain(0b11)), "Test(A | 0x2)");
 }
diff --git a/tests/compile-pass/visibility/bits_field.rs b/tests/compile-pass/visibility/bits_field.rs
--- a/tests/compile-pass/visibility/bits_field.rs
+++ b/tests/compile-pass/visibility/bits_field.rs
@@ -7,5 +7,5 @@ bitflags! {
 }
 
 fn main() {
-    assert_eq!(0b00000001, Flags1::FLAG_A.bits);
+    assert_eq!(0b00000001, Flags1::FLAG_A.bits());
 }
diff --git /dev/null b/tests/smoke-test/Cargo.toml
new file mode 100644
--- /dev/null
+++ b/tests/smoke-test/Cargo.toml
@@ -0,0 +1,8 @@
+[package]
+name = "bitflags-smoke-test"
+version = "0.0.0"
+edition = "2021"
+publish = false
+
+[dependencies.bitflags]
+path = "../../"
diff --git /dev/null b/tests/smoke-test/src/main.rs
new file mode 100644
--- /dev/null
+++ b/tests/smoke-test/src/main.rs
@@ -0,0 +1,15 @@
+use bitflags::bitflags;
+
+bitflags! {
+    #[derive(Debug)]
+    pub struct Flags: u32 {
+        const A = 0b00000001;
+        const B = 0b00000010;
+        const C = 0b00000100;
+        const ABC = Flags::A.bits() | Flags::B.bits() | Flags::C.bits();
+    }
+}
+
+fn main() {
+    println!("{:?}", Flags::ABC);
+}

EOF_114329324912
git status
git diff
cargo test --no-fail-fast
git status
