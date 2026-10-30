import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ecocycle_ai/core/app_state.dart';
import 'package:ecocycle_ai/screens/waste_report_form_screen.dart';

void main() {
  testWidgets('Screen 5: WasteReportFormScreen renders all required components & Route Decision Engine',
      (WidgetTester tester) async {
    final appState = AppState();
    await tester.pumpWidget(MaterialApp(
      home: WasteReportFormScreen(appState: appState),
    ));

    // Verify Title & Subtitle from approved reference
    expect(find.text('Report Waste'), findsOneWidget);
    expect(find.text('Help us keep your area clean'), findsOneWidget);

    // Verify Form Fields
    expect(find.text('Waste Type'), findsOneWidget);
    expect(find.text('Location'), findsOneWidget);
    expect(find.text('Add Photo (optional)'), findsOneWidget);
    expect(find.text('Tap to add photo'), findsOneWidget);
    expect(find.text('Est. Weight (kg)'), findsOneWidget);

    // Verify Route Decision Engine section
    expect(find.text('Route Decision Engine'), findsOneWidget);
    expect(find.text('Rule-Based Municipal Allocation Preview'), findsOneWidget);
    expect(find.text('RULE-BASED'), findsOneWidget);
    expect(find.text('ECO-CART-01'), findsOneWidget);
    expect(find.textContaining('ECO-CART-01'), findsNWidgets(2));

    // Verify Rule-Based Prototype Example card
    expect(find.text('Rule-Based Prototype Example'), findsOneWidget);
    expect(find.textContaining('Area: Residential locality'), findsOneWidget);
    expect(find.textContaining('Selected according to configured area and weight rules'), findsOneWidget);
    expect(find.textContaining('Illustrative rule example'), findsOneWidget);

    // Verify Future Scope section
    expect(find.text('Future Scope'), findsOneWidget);
    expect(find.textContaining('Route Optimisation'), findsOneWidget);
    expect(find.textContaining('Smart Vehicle Assignment'), findsOneWidget);
    expect(find.textContaining('Live Fleet Coordination'), findsOneWidget);

    // Verify Submit CTA Button
    expect(find.text('Submit Report'), findsOneWidget);
  });

  testWidgets('Screen 5: Photo attachment interaction works',
      (WidgetTester tester) async {
    final appState = AppState();
    await tester.pumpWidget(MaterialApp(
      home: WasteReportFormScreen(appState: appState),
    ));

    // Tap the photo attachment box
    await tester.tap(find.text('Tap to add photo'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    // Verify photo attached confirmation
    expect(find.text('Photograph Attached'), findsOneWidget);
    expect(find.text('Ready for collection verification'), findsOneWidget);
  });

  testWidgets('Screen 5: Dynamic route decision updates on stream change',
      (WidgetTester tester) async {
    final appState = AppState();
    await tester.pumpWidget(MaterialApp(
      home: WasteReportFormScreen(
        appState: appState,
        initialCategory: 'hazardous',
      ),
    ));

    // For Hazardous waste, route decision engine should recommend HAZMAT-VAN-03
    expect(find.textContaining('HAZMAT-VAN-03'), findsOneWidget);
    expect(find.textContaining('Certified Hazmat Response Van'), findsOneWidget);
  });

  testWidgets('Screen 5: GPS button tap informs user of device GPS integration status',
      (WidgetTester tester) async {
    final appState = AppState();
    await tester.pumpWidget(MaterialApp(
      home: WasteReportFormScreen(appState: appState),
    ));

    // Tap the GPS button
    await tester.tap(find.byIcon(Icons.my_location_rounded));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    // Verify informative snackbar
    expect(find.textContaining('Live device GPS hardware integration is pending'), findsOneWidget);
  });
}
