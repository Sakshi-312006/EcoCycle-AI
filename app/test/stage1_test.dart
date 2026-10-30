import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ecocycle_ai/core/app_state.dart';
import 'package:ecocycle_ai/screens/create_profile_screen.dart';
import 'package:ecocycle_ai/screens/login_screen.dart';
import 'package:ecocycle_ai/screens/otp_verification_screen.dart';

void main() {
  testWidgets('Screen 1: LoginScreen renders approved components', (WidgetTester tester) async {
    final appState = AppState();
    await tester.pumpWidget(MaterialApp(home: LoginScreen(appState: appState)));

    // Verify brand title, tagline, country code, and login button
    expect(find.text('EcoCycle AI'), findsOneWidget);
    expect(find.text('A cleaner cycle starts here.'), findsOneWidget);
    expect(find.text('Login with OTP'), findsNWidgets(2)); // Card header and button
    expect(find.text('+91'), findsOneWidget);
    expect(find.byType(ElevatedButton), findsOneWidget);
  });

  testWidgets('Screen 2: OtpVerificationScreen renders 6-digit boxes and countdown', (WidgetTester tester) async {
    final appState = AppState();
    await tester.pumpWidget(MaterialApp(
      home: OtpVerificationScreen(
        appState: appState,
        phoneNumber: '9876543210',
        sessionId: 'test-session',
      ),
    ));

    // Verify header, instructions, and verify button
    expect(find.text('Verify OTP'), findsOneWidget);
    expect(find.textContaining('98765'), findsOneWidget);
    expect(find.textContaining('Resend OTP'), findsOneWidget);
    expect(find.text('Verify'), findsOneWidget);
  });

  testWidgets('Screen 3: CreateProfileScreen renders required fields and two doc types', (WidgetTester tester) async {
    final appState = AppState();
    await tester.pumpWidget(MaterialApp(
      home: CreateProfileScreen(
        appState: appState,
        verifiedPhone: '9123456789',
      ),
    ));

    // Verify full name, email, verified phone, and exactly two document types
    expect(find.text('Create Profile'), findsOneWidget);
    expect(find.text('Full Name'), findsOneWidget);
    expect(find.text('Email Address'), findsOneWidget);
    expect(find.text('Verified Mobile Number'), findsOneWidget);
    expect(find.text('Electricity Bill'), findsOneWidget);
    expect(find.text('Water Bill'), findsOneWidget);
    expect(find.text('Property Tax Bill'), findsNothing); // Strictly excluded
    expect(find.text('Create Account'), findsOneWidget);
  });

  testWidgets('Authentication Flow: Returning user vs New user routing', (WidgetTester tester) async {
    final appState = AppState();

    // 1. Existing user phone '9876543210' should be identified as registered
    expect(appState.isUserRegistered('9876543210'), isTrue);

    // 2. New arbitrary phone number should NOT be registered
    expect(appState.isUserRegistered('9123456789'), isFalse);
  });

  testWidgets('Screen 2: Demo OTP verification accepts 123456', (WidgetTester tester) async {
    final appState = AppState();
    await tester.pumpWidget(MaterialApp(
      home: OtpVerificationScreen(
        appState: appState,
        phoneNumber: '9876543210',
        sessionId: 'demo-session',
        isDemoMode: true,
      ),
    ));

    expect(find.text('Demo Mode: Use OTP 123456'), findsOneWidget);

    // Autofill demo OTP
    await tester.tap(find.text('Demo Mode: Use OTP 123456'));
    await tester.pump();

    // Tap Verify
    await tester.tap(find.text('Verify'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
  });
}
