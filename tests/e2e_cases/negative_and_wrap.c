int main() {
    volatile char a = -1;
    volatile char b = -5;
    volatile char c = 0;
    volatile char d = 0;

    c = a + 2;
    d = b << 1;
}
