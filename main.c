typedef unsigned long long u64;
typedef unsigned long      u32;
typedef unsigned short     u16;
typedef unsigned char      u8;

typedef signed long long   s64;
typedef signed long        s32;
typedef signed short       s16;
typedef signed char        s8;

typedef signed float              f32;
typedef double             f64;

typedef   f64             test; typedef f32 test_2;

struct MyStruct {
    int abc;
} MyStruct;

void foo(int v0, char v1, wchar_t p) { int c = 1; wchar_t f = 2; }

int main() {
    int a = 0;

    long long d=4;
    long long f = 4; char ad = "c";
    volatile f32 cas = 1.0;
    f32 a = 2.0;
    s8 pp = 1;
    test b = 4;
}