/* Native FFM ABI regression fixture. Build as a 64-bit shared library. */
#include <stdint.h>
#include <stddef.h>
#include <stdarg.h>
#include <errno.h>
#include <pthread.h>
#if defined(__GNUC__)
#define API __attribute__((visibility("default")))
#else
#define API
#endif
#if defined(__sun) && !defined(_LP64)
#error Solaris Panama fixture must use the 64-bit ABI
#endif
API int8_t nf_i8(int8_t x) { return x; }
API uint8_t nf_u8(uint8_t x) { return x; }
API int16_t nf_i16(int16_t x) { return x; }
API uint16_t nf_u16(uint16_t x) { return x; }
API int32_t nf_i32(int32_t x) { return x; }
API int64_t nf_i64(int64_t x) { return x; }
API float nf_float(float x) { return x; }
API double nf_double(double x) { return x; }
API void* nf_pointer(void* p) { return p; }
API void nf_write(int32_t* p, int32_t x) { *p = x; }
API int64_t nf_many(int64_t a,int64_t b,int64_t c,int64_t d,int64_t e,int64_t f,int64_t g,int64_t h,int64_t i,int64_t j) {
  return a + b*2 + c*3 + d*4 + e*5 + f*6 + g*7 + h*8 + i*9 + j*10;
}
API double nf_mixed(int64_t a,double b,int32_t c,float d,int64_t e,double f,int64_t g,double h,int32_t i,double j) {
  return a + b + c + d + e + f + g + h + i + j;
}
API double nf_fp20(double a,double b,double c,double d,double e,double f,double g,double h,double i,double j,
                   double k,double l,double m,double n,double o,double p,double q,double r,double s,double t) {
  return a+b+c+d+e+f+g+h+i+j+k+l+m+n+o+p+q+r+s+t;
}
typedef struct { double a; int32_t b; } NFPair;
typedef struct { int64_t x[5]; } NFBig;
API NFPair nf_pair(NFPair p, double d, int32_t i) { p.a += d; p.b += i; return p; }
API NFBig nf_big(NFBig b, int64_t d) { for (int i=0;i<5;++i) b.x[i] += d+i; return b; }
API double nf_variadic(int32_t count, ...) {
  va_list ap; va_start(ap,count); double sum=0;
  for(int i=0;i<count;++i) { sum+=va_arg(ap,int); sum+=va_arg(ap,double); }
  va_end(ap); return sum;
}
API int32_t nf_errno(void) { errno=EDOM; return -7; }
API int32_t nf_edom(void) { return EDOM; }
API int32_t nf_heap(unsigned char* p, int32_t n) { for(int i=0;i<n;++i) p[i]=(unsigned char)(0xa0+i); return n; }
API int32_t nf_callback(int32_t (*cb)(int32_t), int32_t n) {
  int32_t sum=0; for(int32_t i=0;i<n;++i) sum+=cb(i); return sum;
}
API int8_t nf_callback_i8(int8_t (*cb)(int8_t), int8_t n) { return cb(n); }
API NFPair nf_callback_pair(NFPair (*cb)(NFPair), NFPair p) { return cb(p); }
struct callback_data { int32_t (*cb)(int32_t); int32_t n,result; };
static void* callback_thread(void* raw) {
  struct callback_data* d=raw;d->result=nf_callback(d->cb,d->n);return NULL;
}
API int32_t nf_pthread_callback(int32_t (*cb)(int32_t), int32_t n) {
  pthread_t t;struct callback_data d={cb,n,0};
  if(pthread_create(&t,NULL,callback_thread,&d)!=0) return INT32_MIN;
  if(pthread_join(t,NULL)!=0) return INT32_MIN;
  return d.result;
}
