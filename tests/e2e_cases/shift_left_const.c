int main() {
    volatile char a = 3;
    volatile char b = 0;
    volatile char c = 0;

    b = a << 2;
    c = 1 << 3;
}
