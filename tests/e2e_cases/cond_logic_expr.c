int main() {
    volatile char a = 0;
    volatile char b = 2;
    volatile char c = 3;
    volatile char r1 = 0;
    volatile char r2 = 0;
    volatile char r3 = 0;
    volatile char r4 = 0;

    r1 = a && b;
    r2 = b && c;
    r3 = a || b;
    r4 = a || 0;
}
