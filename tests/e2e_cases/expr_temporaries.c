int main() {
    volatile char a = 4;
    volatile char b = 3;
    volatile char c = 2;
    volatile char out = 0;

    out = (a + b) ^ (c << 2);
}
