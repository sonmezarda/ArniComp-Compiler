int main() {
    volatile char a = 3;
    volatile char n = 2;
    volatile char z = 0;
    volatile char out1 = 0;
    volatile char out2 = 0;

    out1 = a << n;
    out2 = a << z;
}
