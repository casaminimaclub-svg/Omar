#import <Foundation/Foundation.h>
#import <IOKit/hidsystem/IOHIDEventSystemClient.h>
typedef struct __IOHIDEvent *IOHIDEventRef; typedef struct __IOHIDServiceClient *IOHIDServiceClientRef;
IOHIDEventSystemClientRef IOHIDEventSystemClientCreate(CFAllocatorRef);
int IOHIDEventSystemClientSetMatching(IOHIDEventSystemClientRef, CFDictionaryRef);
IOHIDEventRef IOHIDServiceClientCopyEvent(IOHIDServiceClientRef, int64_t, int32_t, int64_t);
CFStringRef IOHIDServiceClientCopyProperty(IOHIDServiceClientRef, CFStringRef);
double IOHIDEventGetFloatValue(IOHIDEventRef, int32_t);
int main(){@autoreleasepool{
 IOHIDEventSystemClientRef s=IOHIDEventSystemClientCreate(kCFAllocatorDefault);
 IOHIDEventSystemClientSetMatching(s,(__bridge CFDictionaryRef)@{@"PrimaryUsagePage":@(0xff00),@"PrimaryUsage":@(5)});
 for(id x in (__bridge_transfer NSArray*)IOHIDEventSystemClientCopyServices(s)){IOHIDServiceClientRef sc=(__bridge IOHIDServiceClientRef)x;
  NSString*n=(__bridge_transfer NSString*)IOHIDServiceClientCopyProperty(sc,CFSTR("Product"));
  IOHIDEventRef e=IOHIDServiceClientCopyEvent(sc,15,0,0); if(!e)continue; printf("%s %.1f\n",[n UTF8String],IOHIDEventGetFloatValue(e,15<<16)); CFRelease(e);}}}
