int main() {
    volatile char a = 12;
    volatile char b = 10;
    volatile char c = 0;
    volatile char d = 0;
    volatile char e = 0;

    c = a & b;
    d = a ^ b;
    e = a | b;
}
