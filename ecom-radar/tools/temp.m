// Temperatura CPU su Apple Silicon dai sensori HID (nessun permesso speciale): stampa il massimo in °C.
#import <Foundation/Foundation.h>
#import <IOKit/hidsystem/IOHIDEventSystemClient.h>
typedef struct __IOHIDEvent *IOHIDEventRef;
typedef struct __IOHIDServiceClient *IOHIDServiceClientRef;
IOHIDEventSystemClientRef IOHIDEventSystemClientCreate(CFAllocatorRef);
int IOHIDEventSystemClientSetMatching(IOHIDEventSystemClientRef, CFDictionaryRef);
IOHIDEventRef IOHIDServiceClientCopyEvent(IOHIDServiceClientRef, int64_t, int32_t, int64_t);
CFStringRef IOHIDServiceClientCopyProperty(IOHIDServiceClientRef, CFStringRef);
double IOHIDEventGetFloatValue(IOHIDEventRef, int32_t);
int main() {
  @autoreleasepool {
    NSDictionary *m = @{@"PrimaryUsagePage": @(0xff00), @"PrimaryUsage": @(5)};
    IOHIDEventSystemClientRef s = IOHIDEventSystemClientCreate(kCFAllocatorDefault);
    IOHIDEventSystemClientSetMatching(s, (__bridge CFDictionaryRef)m);
    NSArray *svcs = (__bridge_transfer NSArray *)IOHIDEventSystemClientCopyServices(s);
    double mx = 0;
    for (id x in svcs) {
      IOHIDServiceClientRef sc = (__bridge IOHIDServiceClientRef)x;
      NSString *n = (__bridge_transfer NSString *)IOHIDServiceClientCopyProperty(sc, CFSTR("Product"));
      IOHIDEventRef e = IOHIDServiceClientCopyEvent(sc, 15, 0, 0);
      if (!e) continue;
      double t = IOHIDEventGetFloatValue(e, 15 << 16);
      CFRelease(e);
      if ([n hasPrefix:@"PMU tdie"] || [n hasPrefix:@"pACC"] || [n hasPrefix:@"eACC"] || [n containsString:@"tdie"]) if (t > mx && t < 150) mx = t;
    }
    printf("%.0f\n", mx);
  }
}
